#!/usr/bin/env python3
"""Durability layer for the AI-workspaces repo: git sync, status, autosync.

The repo at ~/ai-workspaces (workspaces + skills/ + registry) is the
permanent asset; this script keeps it committed, pushed to its private
remote, and observable. Conflict-safe: a failed rebase never loses work —
local state is pushed to a rescue branch instead.

Stdlib only — must run under plain python3 from any agent, no venv needed.
"""

from __future__ import annotations

import argparse
import re
import socket
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import NoReturn

HOME = Path.home()
REPO = HOME / "ai-workspaces"
LOG_DIR = REPO / ".tmp"
BUNDLE_DIR = HOME / ".ai-workspace-backups" / "bundles"
BUNDLE_KEEP = 14
WARN_FILE_BYTES = 20 * 1024 * 1024
BLOCK_FILE_BYTES = 80 * 1024 * 1024  # GitHub hard-rejects 100MB; stop before that
PLIST_LABEL = "com.ai-workspaces.sync"
PLIST_PATH = HOME / "Library" / "LaunchAgents" / f"{PLIST_LABEL}.plist"
SYNC_INTERVAL_SECONDS = 1800

def _global_git_identity() -> tuple[str, str]:
    """Fall back to the user's global git identity, else a neutral one."""
    import subprocess as _sp

    def _cfg(key: str) -> str:
        r = _sp.run(["git", "config", "--global", key], capture_output=True, text=True)
        return r.stdout.strip()

    return (_cfg("user.name") or "AI Workspaces", _cfg("user.email") or "ai-workspaces@localhost")


GIT_IDENTITY = _global_git_identity()

# High-confidence secret patterns only — this is a tripwire, not a scanner.
SECRET_PATTERNS: dict[str, re.Pattern[str]] = {
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"),
    "Anthropic key": re.compile(r"\bsk-ant-[A-Za-z0-9-]{20,}"),
    "OpenAI-style key": re.compile(r"\bsk-[A-Za-z0-9]{32,}"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "Slack token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}"),
    "Private key block": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "SSN": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
}

# Exit codes: 0 = clean/synced, 1 = pending or error, 2 = conflict.
EXIT_OK = 0
EXIT_PENDING = 1
EXIT_CONFLICT = 2


def fail(message: str, code: int = EXIT_PENDING) -> NoReturn:
    print(f"error: {message}", file=sys.stderr)
    sys.exit(code)


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run git inside the repo, capturing output."""
    result = subprocess.run(
        ["git", "-C", str(REPO), *args],
        capture_output=True,
        text=True,
        errors="replace",  # binary hunks in diffs (e.g. PDFs) must not crash the scan
    )
    if check and result.returncode != 0:
        fail(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result


def notify(title: str, body: str) -> None:
    """Best-effort macOS notification; silent no-op elsewhere."""
    script = f'display notification "{body}" with title "{title}"'
    subprocess.run(["osascript", "-e", script], capture_output=True, check=False)


def ensure_identity() -> None:
    """Make sure commits are possible even on a freshly restored machine."""
    if not git("config", "user.email", check=False).stdout.strip():
        git("config", "user.name", GIT_IDENTITY[0])
        git("config", "user.email", GIT_IDENTITY[1])


def has_remote() -> bool:
    return bool(git("remote", check=False).stdout.strip())


def current_branch() -> str:
    return git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()


def dirty_paths() -> list[str]:
    """Uncommitted paths (staged, unstaged, or untracked)."""
    out = git("status", "--porcelain").stdout
    return [line[3:].strip() for line in out.splitlines() if line.strip()]


def changed_workspaces(paths: list[str]) -> list[str]:
    """Map changed paths to human-level buckets (workspace or system)."""
    buckets: set[str] = set()
    for path in paths:
        top = path.split("/", 1)[0]
        if top in {"skills", "registry.json", "INDEX.md", "README.md", ".gitignore"}:
            buckets.add("system")
        else:
            buckets.add(top)
    return sorted(buckets)


def scan_for_secrets() -> list[str]:
    """Scan lines added by the pending commit for high-confidence secrets.

    Returns:
        Human-readable findings, empty when clean.
    """
    diff = git("diff", "--cached", "--unified=0").stdout
    findings: list[str] = []
    current_file = "?"
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            current_file = line[6:]
        elif line.startswith("+") and not line.startswith("+++"):
            for label, pattern in SECRET_PATTERNS.items():
                if pattern.search(line):
                    findings.append(f"{label} in {current_file}: {line[1:81].strip()}")
    return findings


def oversized_staged_files() -> tuple[list[str], list[str]]:
    """(blocking, warnings) for staged files that are too large for the remote."""
    blocking: list[str] = []
    warnings: list[str] = []
    for name in git("diff", "--cached", "--name-only").stdout.splitlines():
        path = REPO / name
        if not path.is_file():
            continue
        size = path.stat().st_size
        if size > BLOCK_FILE_BYTES:
            blocking.append(f"{name} ({size // (1024 * 1024)}MB)")
        elif size > WARN_FILE_BYTES:
            warnings.append(f"{name} ({size // (1024 * 1024)}MB)")
    return blocking, warnings


def write_bundle() -> str | None:
    """Snapshot the whole repo into a rotated local git bundle.

    An independent backup leg: bundles survive corruption or loss of the
    GitHub remote and restore with plain `git clone <bundle>`. Best-effort —
    a bundle failure never fails the sync.

    Returns:
        The bundle path written, or None on failure.
    """
    try:
        BUNDLE_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        path = BUNDLE_DIR / f"ai-workspaces-{stamp}.bundle"
        result = git("bundle", "create", str(path), "--all", check=False)
        if result.returncode != 0:
            return None
        bundles = sorted(BUNDLE_DIR.glob("ai-workspaces-*.bundle"))
        for old in bundles[:-BUNDLE_KEEP]:
            old.unlink()
        return str(path)
    except OSError:
        return None


def latest_bundle() -> Path | None:
    bundles = sorted(BUNDLE_DIR.glob("ai-workspaces-*.bundle"))
    return bundles[-1] if bundles else None


def ahead_behind() -> tuple[int, int] | None:
    """(ahead, behind) vs the remote branch, or None when no upstream exists."""
    result = git(
        "rev-list", "--left-right", "--count", "HEAD...@{upstream}", check=False
    )
    if result.returncode != 0:
        return None
    ahead, behind = result.stdout.split()
    return int(ahead), int(behind)


def cmd_status(_args: argparse.Namespace) -> None:
    if not (REPO / ".git").is_dir():
        fail(f"{REPO} is not a git repo — run workspace.py bootstrap first")
    pending = dirty_paths()
    counts = ahead_behind()
    last_commit = git(
        "log", "-1", "--format=%h %ad %s", "--date=format:%Y-%m-%d %H:%M"
    ).stdout.strip()

    print(f"repo:        {REPO}")
    print(f"branch:      {current_branch()}")
    print(f"last commit: {last_commit}")
    bundle = latest_bundle()
    if bundle:
        age_h = (datetime.now().timestamp() - bundle.stat().st_mtime) / 3600
        print(f"bundle:      {bundle.name} ({age_h:.1f}h old)")
    else:
        print("bundle:      none yet (written after each successful push)")

    if pending:
        print(
            f"uncommitted: {len(pending)} file(s) in: {', '.join(changed_workspaces(pending))}"
        )
    else:
        print("uncommitted: none")

    if not has_remote():
        print("remote:      NONE — repo is local-only, laptop loss loses everything")
        sys.exit(EXIT_PENDING)
    if counts is None:
        print("remote:      configured, but branch has no upstream yet (push needed)")
        sys.exit(EXIT_PENDING)
    ahead, behind = counts
    rescue = git(
        "branch", "-r", "--list", "origin/conflict/*", check=False
    ).stdout.strip()
    if rescue:
        print(f"CONFLICT:    unmerged rescue branch(es) on remote:\n{rescue}")
        sys.exit(EXIT_CONFLICT)
    if ahead == 0 and behind == 0 and not pending:
        print("backup:      ✓ fully synchronized with remote")
        sys.exit(EXIT_OK)
    state = []
    if ahead:
        state.append(f"{ahead} commit(s) not pushed")
    if behind:
        state.append(f"{behind} commit(s) not pulled")
    if pending:
        state.append("uncommitted local changes")
    print(f"backup:      ✗ awaiting sync — {'; '.join(state)}")
    sys.exit(EXIT_PENDING)


def rescue_push(quiet: bool) -> NoReturn:
    """Push local HEAD to a rescue branch so a conflict never strands work."""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    host = socket.gethostname().split(".")[0].lower()
    branch = f"conflict/{host}-{stamp}"
    push = git("push", "origin", f"HEAD:refs/heads/{branch}", check=False)
    if push.returncode == 0:
        message = (
            f"rebase conflict: local work saved to remote branch {branch!r}; "
            "reconcile manually (git pull --rebase, resolve, push, delete branch)"
        )
    else:
        message = (
            "rebase conflict AND rescue push failed — local work is committed "
            f"locally only; resolve by hand in {REPO}"
        )
    print(f"CONFLICT: {message}", file=sys.stderr)
    if quiet:
        notify("AI workspaces sync", "Conflict — run: workspace.py status")
    sys.exit(EXIT_CONFLICT)


def cmd_now(args: argparse.Namespace) -> None:
    if not (REPO / ".git").is_dir():
        fail(f"{REPO} is not a git repo — run workspace.py bootstrap first")
    ensure_identity()

    pending = dirty_paths()
    if pending:
        git("add", "-A")
        blocking, warnings = oversized_staged_files()
        for warning in warnings:
            print(f"warning: large file {warning} — the repo is for text + photos")
        if blocking:
            git("reset", check=False)
            for name in blocking:
                print(
                    f"BLOCKED: file too large for the remote: {name}", file=sys.stderr
                )
            if args.quiet:
                notify("AI workspaces sync", "Blocked: file too large to back up")
            fail(
                "files over 80MB cannot go to GitHub — keep large media elsewhere "
                "and reference it from the workspace"
            )
        findings = scan_for_secrets()
        if findings and not args.force_secrets:
            git("reset", check=False)
            for finding in findings:
                print(f"BLOCKED: possible {finding}", file=sys.stderr)
            if args.quiet:
                notify("AI workspaces sync", "Blocked: possible secret in changes")
            fail(
                "possible secrets in pending changes — remove them (credentials "
                "never belong in workspaces) or re-run with --force-secrets"
            )
        host = socket.gethostname().split(".")[0]
        summary = ", ".join(changed_workspaces(pending))
        git("commit", "-q", "-m", f"sync from {host}: {summary}")
        print(f"committed {len(pending)} file(s): {summary}")
    else:
        print("nothing to commit")

    if not has_remote():
        print(
            "no remote configured — commit is local-only (add one for real durability)"
        )
        sys.exit(EXIT_OK)

    fetch = git("fetch", "origin", check=False)
    if fetch.returncode != 0:
        message = f"fetch failed (offline?): {fetch.stderr.strip()}"
        if args.quiet:
            print(message, file=sys.stderr)
            sys.exit(EXIT_PENDING)  # autosync retries on its own schedule
        fail(message)

    branch = current_branch()
    if git("rev-parse", "--verify", f"origin/{branch}", check=False).returncode == 0:
        rebase = git("rebase", "--autostash", f"origin/{branch}", check=False)
        if rebase.returncode != 0:
            git("rebase", "--abort", check=False)
            rescue_push(args.quiet)

    push = git("push", "-u", "origin", branch, check=False)
    if push.returncode != 0:
        message = f"push failed: {push.stderr.strip()}"
        if args.quiet:
            notify("AI workspaces sync", "Push failed — run: workspace.py status")
            print(message, file=sys.stderr)
            sys.exit(EXIT_PENDING)
        fail(message)
    bundle = write_bundle()
    if bundle:
        print(f"✓ synchronized with remote (local bundle: {bundle})")
    else:
        print("✓ synchronized with remote (warning: local bundle failed)")
    sys.exit(EXIT_OK)


def cmd_install_autosync(_args: argparse.Namespace) -> None:
    LOG_DIR.mkdir(exist_ok=True)
    script = Path(__file__).resolve()
    plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>{PLIST_LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>{script}</string>
        <string>now</string>
        <string>--quiet</string>
    </array>
    <key>StartInterval</key><integer>{SYNC_INTERVAL_SECONDS}</integer>
    <key>RunAtLoad</key><true/>
    <key>StandardOutPath</key><string>{LOG_DIR}/autosync.log</string>
    <key>StandardErrorPath</key><string>{LOG_DIR}/autosync.log</string>
</dict>
</plist>
"""
    PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    PLIST_PATH.write_text(plist)
    subprocess.run(["launchctl", "unload", str(PLIST_PATH)], capture_output=True)
    result = subprocess.run(
        ["launchctl", "load", str(PLIST_PATH)], capture_output=True, text=True
    )
    if result.returncode != 0:
        fail(f"launchctl load failed: {result.stderr.strip()}")
    print(
        f"autosync installed: every {SYNC_INTERVAL_SECONDS // 60} min via {PLIST_PATH}"
    )
    print(f"log: {LOG_DIR}/autosync.log")


def cmd_uninstall_autosync(_args: argparse.Namespace) -> None:
    if not PLIST_PATH.exists():
        print("autosync is not installed")
        return
    subprocess.run(["launchctl", "unload", str(PLIST_PATH)], capture_output=True)
    PLIST_PATH.unlink()
    print("autosync removed")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="sync.py",
        description="Git durability layer for ~/ai-workspaces (status, sync, autosync).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_status = sub.add_parser(
        "status", help="show sync/backup state (exit 0 only when fully synced)"
    )
    p_status.set_defaults(func=cmd_status)

    p_now = sub.add_parser("now", help="commit all changes, pull --rebase, push")
    p_now.add_argument(
        "--quiet", action="store_true", help="autosync mode: notify on failure"
    )
    p_now.add_argument(
        "--force-secrets",
        action="store_true",
        help="commit even if the secret tripwire fires (be sure!)",
    )
    p_now.set_defaults(func=cmd_now)

    p_install = sub.add_parser(
        "install-autosync", help="install launchd agent (every 30 min)"
    )
    p_install.set_defaults(func=cmd_install_autosync)

    p_uninstall = sub.add_parser("uninstall-autosync", help="remove the launchd agent")
    p_uninstall.set_defaults(func=cmd_uninstall_autosync)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
