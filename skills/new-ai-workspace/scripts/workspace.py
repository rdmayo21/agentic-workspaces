#!/usr/bin/env python3
"""Deterministic manager for persistent AI workspaces.

Creates, lists, archives, repairs, and deletes workspaces under
~/ai-workspaces/ (a git repo — the durable asset), each paired with a thin
project skill at ~/ai-workspaces/skills/<name>/ (canonically addressed as
~/.ai/skills/<name>/ via symlink) exposed to Claude Code (~/.claude/skills/),
Codex (~/.agents/skills/), and Gemini CLI (~/.gemini/commands/<name>.toml).
The AI layer decides WHAT to create; this script makes the filesystem
mechanics reliable and idempotent. Durability (git sync, autosync, backup
status) lives in sync.py next to this script.

Stdlib only — must run under plain python3 from any agent, no venv needed.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import NoReturn

HOME = Path.home()
WORKSPACES_DIR = HOME / "ai-workspaces"
CANONICAL_SKILLS_DIR = HOME / ".ai" / "skills"
REPO_SKILLS_DIR = WORKSPACES_DIR / "skills"  # real home; ~/.ai/skills symlinks here
LINK_DIRS = (HOME / ".claude" / "skills", HOME / ".agents" / "skills")
GEMINI_DIR = HOME / ".gemini"
GEMINI_COMMANDS_DIR = GEMINI_DIR / "commands"
REGISTRY_PATH = WORKSPACES_DIR / "registry.json"
INDEX_PATH = WORKSPACES_DIR / "INDEX.md"

SKILL_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = SKILL_ROOT / "assets"
BASE_ASSETS_DIR = ASSETS_DIR / "base"
PROJECT_SKILL_TEMPLATE = ASSETS_DIR / "project-skill-template.md"

NAME_RE = re.compile(r"^[a-z][a-z0-9-]{1,49}$")
RESERVED_NAMES = {"archived", "capture", "media", "new-ai-workspace", "skills"}


@dataclass
class WorkspaceEntry:
    """One workspace's registry record."""

    name: str
    type: str
    status: str
    created: str
    description: str
    archived: str | None = None
    managed: bool = True  # False for adopted workspaces with their own file layout

    def to_dict(self) -> dict[str, str | bool | None]:
        return {
            "type": self.type,
            "status": self.status,
            "created": self.created,
            "description": self.description,
            "archived": self.archived,
            "managed": self.managed,
        }


@dataclass
class Registry:
    """All known workspaces, persisted as JSON (INDEX.md is derived from this)."""

    entries: dict[str, WorkspaceEntry] = field(default_factory=dict)

    @classmethod
    def load(cls) -> Registry:
        if not REGISTRY_PATH.exists():
            return cls()
        try:
            raw = json.loads(REGISTRY_PATH.read_text())
        except json.JSONDecodeError as exc:
            fail(f"registry is corrupt, fix it by hand first: {REGISTRY_PATH} ({exc})")
        entries = {
            name: WorkspaceEntry(name=name, **data)
            for name, data in raw.get("workspaces", {}).items()
        }
        return cls(entries=entries)

    def save(self) -> None:
        WORKSPACES_DIR.mkdir(parents=True, exist_ok=True)
        payload = {
            "workspaces": {
                name: e.to_dict() for name, e in sorted(self.entries.items())
            }
        }
        REGISTRY_PATH.write_text(json.dumps(payload, indent=2) + "\n")
        write_index(self)


def fail(message: str) -> NoReturn:
    """Print an error and exit non-zero."""
    print(f"error: {message}", file=sys.stderr)
    sys.exit(1)


def normalize_name(raw: str) -> str:
    """Normalize a project name to a valid skill/directory slug.

    Args:
        raw: User-supplied name, e.g. "Tokyo Trip 2027".

    Returns:
        Lowercase hyphenated slug, e.g. "tokyo-trip-2027".
    """
    slug = raw.strip().lower()
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    if not NAME_RE.match(slug):
        fail(
            f"cannot derive a valid name from {raw!r} (got {slug!r}); "
            "names must start with a letter, use only a-z 0-9 and hyphens, max 50 chars"
        )
    if slug in RESERVED_NAMES:
        fail(f"{slug!r} is a reserved name")
    return slug


def title_from_name(name: str) -> str:
    return name.replace("-", " ").title()


def render(text: str, mapping: dict[str, str]) -> str:
    """Substitute {{key}} placeholders; unknown placeholders are left intact."""
    for key, value in mapping.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def available_types() -> list[str]:
    return sorted(
        d.name for d in ASSETS_DIR.iterdir() if d.is_dir() and d.name != "base"
    )


def workspace_dir(name: str) -> Path:
    return WORKSPACES_DIR / name


def skill_dir(name: str) -> Path:
    return CANONICAL_SKILLS_DIR / name


def copy_template_tree(
    src_dir: Path, dest_dir: Path, mapping: dict[str, str]
) -> list[str]:
    """Render every template in src_dir into dest_dir, skipping files that exist.

    Returns:
        Names of files actually written.
    """
    written: list[str] = []
    for src in sorted(src_dir.iterdir()):
        if not src.is_file():
            continue
        dest = dest_dir / src.name
        if dest.exists():
            continue
        dest.write_text(render(src.read_text(), mapping))
        written.append(src.name)
    return written


def link_path_status(link: Path, target: Path) -> str:
    """Classify a would-be symlink location: 'ok', 'missing', or 'conflict'."""
    if not link.exists() and not link.is_symlink():
        return "missing"
    if link.is_symlink() and link.resolve() == target.resolve():
        return "ok"
    return "conflict"


def ensure_links(name: str) -> list[str]:
    """Create/repair symlinks in each provider skills dir; fail on foreign conflicts.

    Returns:
        Human-readable notes about what was done.
    """
    target = skill_dir(name)
    notes: list[str] = []
    for link_dir in LINK_DIRS:
        link_dir.mkdir(parents=True, exist_ok=True)
        link = link_dir / name
        status = link_path_status(link, target)
        if status == "ok":
            continue
        if status == "conflict":
            if link.is_symlink():
                # Broken/stale symlinks are safe to replace; real dirs/files never are.
                link.unlink()
                notes.append(f"replaced stale symlink {link}")
            else:
                fail(
                    f"{link} already exists and is not a symlink to {target} — "
                    f"a skill named {name!r} already exists there; pick another name"
                )
        rel_target = Path("../..") / target.relative_to(HOME)
        link.symlink_to(rel_target)
        notes.append(f"linked {link} -> {rel_target}")
    return notes


def toml_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def ensure_gemini_command(name: str, description: str) -> str | None:
    """Write ~/.gemini/commands/<name>.toml so /<name> works in Gemini CLI.

    Returns:
        A note about what was written, or None when Gemini CLI isn't set up
        on this machine (we never create ~/.gemini ourselves).
    """
    if not GEMINI_DIR.is_dir():
        return None
    GEMINI_COMMANDS_DIR.mkdir(parents=True, exist_ok=True)
    path = GEMINI_COMMANDS_DIR / f"{name}.toml"
    ws = workspace_dir(name)
    skill_md = REPO_SKILLS_DIR / name / "SKILL.md"
    prompt = (
        f"You are working in the persistent '{name}' AI workspace. "
        f"First read {skill_md} and follow its instructions. "
        f"The workspace lives at {ws}/ — read STATUS.md (and AGENTS.md if present) "
        "before acting, and record any durable conclusions or changes in the "
        "workspace files, then run "
        f"'python3 {REPO_SKILLS_DIR}/new-ai-workspace/scripts/sync.py now' "
        "so the update is backed up. User request: "
    ) + "{{args}}"
    body = (
        f'description = "{toml_escape(description)}"\n\nprompt = """\n{prompt}\n"""\n'
    )
    path.write_text(body)
    return f"wrote {path}"


def remove_gemini_command(name: str) -> None:
    path = GEMINI_COMMANDS_DIR / f"{name}.toml"
    if path.exists():
        path.unlink()
        print(f"removed {path}")


def validate_skill_md(path: Path, name: str) -> None:
    """Sanity-check generated SKILL.md frontmatter (name present and matching)."""
    text = path.read_text()
    if not text.startswith("---"):
        fail(f"{path} is missing YAML frontmatter")
    frontmatter = text.split("---", 2)[1]
    if f"name: {name}" not in frontmatter:
        fail(f"{path} frontmatter name does not match {name!r}")
    if "description:" not in frontmatter:
        fail(f"{path} frontmatter is missing a description")
    if "{{" in text:
        fail(f"{path} still contains unrendered placeholders")


def last_updated(name: str) -> str:
    """Most recent mtime across the workspace's markdown files, as YYYY-MM-DD."""
    ws = workspace_dir(name)
    if not ws.is_dir():
        return "missing"
    mtimes = [p.stat().st_mtime for p in ws.rglob("*.md")]
    if not mtimes:
        return "-"
    return datetime.fromtimestamp(max(mtimes)).date().isoformat()


def write_index(registry: Registry) -> None:
    """Regenerate INDEX.md from the registry (never parsed, only written)."""
    lines = ["# AI workspaces", ""]
    live = [e for e in registry.entries.values() if e.status != "archived"]
    dead = [e for e in registry.entries.values() if e.status == "archived"]
    lines += [
        "## Active",
        "",
        "| Workspace | Type | Status | Last updated | Description |",
        "|---|---|---|---|---|",
    ]
    for e in sorted(live, key=lambda e: e.name):
        lines.append(
            f"| [{e.name}]({e.name}/) | {e.type} | {e.status} | "
            f"{last_updated(e.name)} | {e.description} |"
        )
    if not live:
        lines.append("| _none_ | | | | |")
    lines += [
        "",
        "## Archived",
        "",
        "| Workspace | Type | Archived | Description |",
        "|---|---|---|---|",
    ]
    for e in sorted(dead, key=lambda e: e.name):
        lines.append(f"| {e.name} | {e.type} | {e.archived or '?'} | {e.description} |")
    if not dead:
        lines.append("| _none_ | | | |")
    lines += [
        "",
        "_Generated by new-ai-workspace; edit registry.json via the script, not here._",
    ]
    INDEX_PATH.write_text("\n".join(lines) + "\n")


def build_mapping(
    name: str, ws_type: str, description: str, skill_description: str
) -> dict[str, str]:
    return {
        "name": name,
        "title": title_from_name(name),
        "date": date.today().isoformat(),
        "type": ws_type,
        "description": description,
        "skill_description": skill_description,
        "workspace_path": str(workspace_dir(name)),
    }


def default_skill_description(name: str, description: str) -> str:
    title = title_from_name(name)
    return (
        f"Manage the persistent '{title}' workspace at ~/ai-workspaces/{name}/. "
        f"{description} USE THIS SKILL whenever the user mentions {title.lower()} or wants to "
        f"continue, review, or update this ongoing project. Invoke with /{name}."
    )


def create_project_skill(mapping: dict[str, str]) -> Path:
    """Generate ~/.ai/skills/<name>/SKILL.md from the template and validate it."""
    sdir = skill_dir(mapping["name"])
    sdir.mkdir(parents=True, exist_ok=True)
    skill_md = sdir / "SKILL.md"
    if not skill_md.exists():
        skill_md.write_text(render(PROJECT_SKILL_TEMPLATE.read_text(), mapping))
    validate_skill_md(skill_md, mapping["name"])
    return skill_md


def cmd_create(args: argparse.Namespace) -> None:
    name = normalize_name(args.name)
    if name != args.name:
        print(f"note: normalized name {args.name!r} -> {name!r}")
    ws_type = args.type
    if ws_type != "general" and ws_type not in available_types():
        fail(
            f"unknown type {ws_type!r}; available: general, {', '.join(available_types())}"
        )

    ws = workspace_dir(name)
    sdir = skill_dir(name)
    if ws.exists():
        fail(
            f"workspace already exists: {ws} (use 'repair {name}' to fix a broken one)"
        )
    if sdir.exists():
        fail(
            f"skill dir already exists: {sdir} (use 'repair {name}' or pick another name)"
        )
    for link_dir in LINK_DIRS:
        link = link_dir / name
        if link_path_status(link, sdir) == "conflict":
            fail(
                f"{link} already exists and is not ours — a skill named {name!r} is taken"
            )

    description = (
        args.description or f"Persistent workspace for {title_from_name(name)}."
    )
    skill_description = args.skill_description or default_skill_description(
        name, description
    )
    mapping = build_mapping(name, ws_type, description, skill_description)

    plan = [f"create {ws}/ (base files + archive/)"]
    if ws_type != "general":
        overlay_files = ", ".join(
            sorted(p.name for p in (ASSETS_DIR / ws_type).iterdir())
        )
        plan.append(f"add {ws_type} overlay: {overlay_files}")
    for extra in args.extra:
        plan.append(f"add empty extra file: {extra}")
    plan.append(f"generate {sdir}/SKILL.md")
    plan += [f"symlink {d / name} -> {sdir}" for d in LINK_DIRS]
    plan.append("register in registry.json and regenerate INDEX.md")

    if args.dry_run:
        print("dry run — would do:")
        for step in plan:
            print(f"  - {step}")
        return

    ws.mkdir(parents=True)
    (ws / "archive").mkdir()
    copy_template_tree(BASE_ASSETS_DIR, ws, mapping)
    if ws_type != "general":
        copy_template_tree(ASSETS_DIR / ws_type, ws, mapping)
    for extra in args.extra:
        extra_name = extra if extra.endswith(".md") else f"{extra}.md"
        extra_path = ws / extra_name
        if not extra_path.exists():
            stem = extra_path.stem.replace("-", " ").replace("_", " ").title()
            extra_path.write_text(f"# {stem}\n\n(to be filled in)\n")

    create_project_skill(mapping)
    for note in ensure_links(name):
        print(note)
    gemini_note = ensure_gemini_command(name, description)
    if gemini_note:
        print(gemini_note)

    registry = Registry.load()
    registry.entries[name] = WorkspaceEntry(
        name=name,
        type=ws_type,
        status=args.status,
        created=date.today().isoformat(),
        description=description,
    )
    registry.save()

    print(f"created workspace: {ws}")
    print(f"created skill:     {sdir}/SKILL.md")
    print(
        f"invoke with:       /{name} (Claude Code) or ${name} (Codex), after next session start"
    )


def cmd_list(_args: argparse.Namespace) -> None:
    registry = Registry.load()
    if not registry.entries:
        print("no workspaces registered yet")
        return
    registry.save()  # refreshes INDEX.md's last-updated column
    width = max(len(n) for n in registry.entries)
    for entry in sorted(
        registry.entries.values(), key=lambda e: (e.status == "archived", e.name)
    ):
        print(
            f"{entry.name:<{width}}  {entry.type:<10} {entry.status:<10} "
            f"updated {last_updated(entry.name)}  {entry.description}"
        )
    print(f"\nindex: {INDEX_PATH}")


def cmd_archive(args: argparse.Namespace) -> None:
    name = normalize_name(args.name)
    registry = Registry.load()
    entry = registry.entries.get(name)
    if entry is None:
        fail(f"unknown workspace {name!r} (see 'list')")
    if entry.status == "archived":
        fail(f"{name} is already archived")

    ws = workspace_dir(name)
    sdir = skill_dir(name)
    skill_md = sdir / "SKILL.md"
    if ws.is_dir() and skill_md.exists():
        (ws / "archive").mkdir(exist_ok=True)
        shutil.copy2(skill_md, ws / "archive" / "SKILL.md")
        print(f"preserved skill at {ws / 'archive' / 'SKILL.md'}")
    for link_dir in LINK_DIRS:
        link = link_dir / name
        if link.is_symlink() and link_path_status(link, sdir) == "ok":
            link.unlink()
            print(f"removed {link}")
    if sdir.is_dir():
        shutil.rmtree(sdir)
        print(f"removed {sdir}")
    remove_gemini_command(name)

    entry.status = "archived"
    entry.archived = date.today().isoformat()
    registry.save()
    print(
        f"archived {name}; workspace files remain at {ws} — 'repair {name}' reactivates it"
    )


def cmd_repair(args: argparse.Namespace) -> None:
    name = normalize_name(args.name)
    registry = Registry.load()
    entry = registry.entries.get(name)
    ws = workspace_dir(name)
    if entry is None and not ws.is_dir():
        fail(f"nothing to repair: {name!r} has no registry entry and no workspace dir")
    if entry is None:
        entry = WorkspaceEntry(
            name=name,
            type="general",
            status="active",
            created=date.today().isoformat(),
            description=f"Persistent workspace for {title_from_name(name)}.",
        )
        registry.entries[name] = entry
        print(
            f"re-registered {name} (type/description unknown — edit registry.json if wrong)"
        )

    description = entry.description
    mapping = build_mapping(
        name, entry.type, description, default_skill_description(name, description)
    )

    ws.mkdir(parents=True, exist_ok=True)
    (ws / "archive").mkdir(exist_ok=True)
    if entry.managed:
        restored = copy_template_tree(BASE_ASSETS_DIR, ws, mapping)
        for fname in restored:
            print(f"restored missing base file: {fname}")
    else:
        print("adopted workspace (own layout) — skipping base-file restoration")

    sdir = skill_dir(name)
    if not (sdir / "SKILL.md").exists():
        preserved = ws / "archive" / "SKILL.md"
        if preserved.exists():
            sdir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(preserved, sdir / "SKILL.md")
            print(f"restored SKILL.md from {preserved}")
        else:
            create_project_skill(mapping)
            print("regenerated SKILL.md from template")
    validate_skill_md(sdir / "SKILL.md", name)
    for note in ensure_links(name):
        print(note)
    gemini_note = ensure_gemini_command(name, description)
    if gemini_note:
        print(gemini_note)

    if entry.status == "archived":
        entry.status = "active"
        entry.archived = None
        print(f"reactivated {name}")
    registry.save()
    print(f"repair complete: {name}")


def cmd_adopt(args: argparse.Namespace) -> None:
    """Register an existing workspace + skill without touching any files.

    For migrating pre-existing projects into the system: the caller places
    files at ~/ai-workspaces/<name>/ and a SKILL.md at ~/.ai/skills/<name>/
    first; adopt validates, symlinks, and registers them.
    """
    name = normalize_name(args.name)
    if args.type != "general" and args.type not in available_types():
        fail(
            f"unknown type {args.type!r}; available: general, {', '.join(available_types())}"
        )
    registry = Registry.load()
    if name in registry.entries:
        fail(f"{name} is already registered (see 'list')")
    ws = workspace_dir(name)
    if not ws.is_dir():
        fail(f"no workspace dir at {ws} — put the project files there first")
    skill_md = skill_dir(name) / "SKILL.md"
    if not skill_md.exists():
        fail(f"no skill at {skill_md} — create the project SKILL.md there first")
    validate_skill_md(skill_md, name)

    (ws / "archive").mkdir(exist_ok=True)
    for note in ensure_links(name):
        print(note)
    gemini_note = ensure_gemini_command(
        name, args.description or f"Persistent workspace for {title_from_name(name)}."
    )
    if gemini_note:
        print(gemini_note)
    registry.entries[name] = WorkspaceEntry(
        name=name,
        type=args.type,
        status="active",
        created=args.created or date.today().isoformat(),
        description=args.description
        or f"Persistent workspace for {title_from_name(name)}.",
        managed=False,
    )
    registry.save()
    print(f"adopted {name}: files untouched, symlinks + registry entry created")


def cmd_delete(args: argparse.Namespace) -> None:
    name = normalize_name(args.name)
    if not args.yes:
        fail("delete is destructive; re-run with --yes to confirm")
    registry = Registry.load()
    ws = workspace_dir(name)
    sdir = skill_dir(name)
    for link_dir in LINK_DIRS:
        link = link_dir / name
        if link.is_symlink() and link_path_status(link, sdir) == "ok":
            link.unlink()
            print(f"removed {link}")
    for path in (sdir, ws):
        if path.is_dir():
            shutil.rmtree(path)
            print(f"removed {path}")
    remove_gemini_command(name)
    if name in registry.entries:
        del registry.entries[name]
        registry.save()
        print(f"unregistered {name}")


def cmd_bootstrap(_args: argparse.Namespace) -> None:
    """Re-wire a machine after cloning the repo to ~/ai-workspaces.

    Recreates the ~/.ai/skills compat symlink, every provider symlink, and
    Gemini commands for all non-archived workspaces. Touches no workspace
    content — safe to run repeatedly.
    """
    if not WORKSPACES_DIR.is_dir():
        fail(f"nothing at {WORKSPACES_DIR} — clone the ai-workspaces repo there first")
    if not REPO_SKILLS_DIR.is_dir():
        fail(f"{REPO_SKILLS_DIR} missing — is this a complete clone of the repo?")

    (HOME / ".ai").mkdir(exist_ok=True)
    if CANONICAL_SKILLS_DIR.is_symlink():
        if CANONICAL_SKILLS_DIR.resolve() != REPO_SKILLS_DIR.resolve():
            CANONICAL_SKILLS_DIR.unlink()
    elif CANONICAL_SKILLS_DIR.exists():
        fail(
            f"{CANONICAL_SKILLS_DIR} is a real directory — move it aside first "
            "(its contents belong in the repo's skills/)"
        )
    if not CANONICAL_SKILLS_DIR.is_symlink():
        CANONICAL_SKILLS_DIR.symlink_to(Path("..") / "ai-workspaces" / "skills")
        print(f"linked {CANONICAL_SKILLS_DIR} -> ../ai-workspaces/skills")

    if (WORKSPACES_DIR / ".git").is_dir():
        identity = subprocess.run(
            ["git", "-C", str(WORKSPACES_DIR), "config", "user.email"],
            capture_output=True,
            text=True,
        )
        if not identity.stdout.strip():
            gname = subprocess.run(
                ["git", "config", "--global", "user.name"],
                capture_output=True,
                text=True,
            ).stdout.strip()
            gemail = subprocess.run(
                ["git", "config", "--global", "user.email"],
                capture_output=True,
                text=True,
            ).stdout.strip()
            if gname and gemail:
                subprocess.run(
                    ["git", "-C", str(WORKSPACES_DIR), "config", "user.name", gname],
                    check=True,
                )
                subprocess.run(
                    ["git", "-C", str(WORKSPACES_DIR), "config", "user.email", gemail],
                    check=True,
                )
                print("set repo-local git identity from global git config")
            else:
                print("note: no git identity configured — run 'git config --global user.name/user.email'")

    registry = Registry.load()
    names = ["new-ai-workspace"] + [
        e.name for e in registry.entries.values() if e.status != "archived"
    ]
    for name in names:
        if not (skill_dir(name) / "SKILL.md").exists():
            print(f"warning: no SKILL.md for {name!r}; run 'repair {name}'")
            continue
        for note in ensure_links(name):
            print(note)
        entry = registry.entries.get(name)
        gemini_note = ensure_gemini_command(
            name, entry.description if entry else "Workspace system manager."
        )
        if gemini_note:
            print(gemini_note)
    registry.save()
    print(f"bootstrap complete: {len(names)} skill(s) wired for Claude Code + Codex")
    print("next: restart agent sessions; run 'sync.py install-autosync' for autosync")


def run_sync(*sync_args: str) -> NoReturn:
    """Delegate to sync.py next to this script, propagating the exit code."""
    sync_script = Path(__file__).resolve().parent / "sync.py"
    result = subprocess.run([sys.executable, str(sync_script), *sync_args])
    sys.exit(result.returncode)


def cmd_sync(_args: argparse.Namespace) -> None:
    run_sync("now")


def cmd_status(_args: argparse.Namespace) -> None:
    run_sync("status")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="workspace.py",
        description="Deterministic manager for persistent AI workspaces (~/ai-workspaces).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_create = sub.add_parser(
        "create", help="create a workspace + project skill + symlinks"
    )
    p_create.add_argument("name", help="project name (will be normalized to a slug)")
    p_create.add_argument(
        "--type",
        default="general",
        help=f"workspace type: general, {', '.join(available_types())}",
    )
    p_create.add_argument(
        "--description",
        default=None,
        help="one-line description of the project (used in files + registry)",
    )
    p_create.add_argument(
        "--skill-description",
        default=None,
        help="full frontmatter description for the generated project skill",
    )
    p_create.add_argument(
        "--extra",
        action="append",
        default=[],
        help="extra markdown file to create (repeatable), e.g. --extra METRICS",
    )
    p_create.add_argument(
        "--status",
        default="active",
        choices=("active", "incubating"),
        help="initial registry status",
    )
    p_create.add_argument(
        "--dry-run", action="store_true", help="print the plan, change nothing"
    )
    p_create.set_defaults(func=cmd_create)

    p_list = sub.add_parser("list", help="list workspaces and refresh INDEX.md")
    p_list.set_defaults(func=cmd_list)

    p_archive = sub.add_parser(
        "archive", help="retire a workspace: remove its skill + links, keep files"
    )
    p_archive.add_argument("name")
    p_archive.set_defaults(func=cmd_archive)

    p_repair = sub.add_parser(
        "repair", help="restore missing files/skill/symlinks; reactivates if archived"
    )
    p_repair.add_argument("name")
    p_repair.set_defaults(func=cmd_repair)

    p_adopt = sub.add_parser(
        "adopt",
        help="register an existing workspace + skill (migration; touches no files)",
    )
    p_adopt.add_argument("name")
    p_adopt.add_argument("--type", default="general")
    p_adopt.add_argument("--description", default=None)
    p_adopt.add_argument(
        "--created", default=None, help="original creation date, YYYY-MM-DD"
    )
    p_adopt.set_defaults(func=cmd_adopt)

    p_delete = sub.add_parser(
        "delete", help="permanently delete a workspace AND its skill"
    )
    p_delete.add_argument("name")
    p_delete.add_argument(
        "--yes", action="store_true", help="confirm permanent deletion"
    )
    p_delete.set_defaults(func=cmd_delete)

    p_bootstrap = sub.add_parser(
        "bootstrap",
        help="re-wire a machine after cloning the repo (symlinks, identity, Gemini)",
    )
    p_bootstrap.set_defaults(func=cmd_bootstrap)

    p_sync = sub.add_parser("sync", help="commit + push everything (sync.py now)")
    p_sync.set_defaults(func=cmd_sync)

    p_status = sub.add_parser("status", help="show backup/sync state (sync.py status)")
    p_status.set_defaults(func=cmd_status)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
