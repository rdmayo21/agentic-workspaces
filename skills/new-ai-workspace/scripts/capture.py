#!/usr/bin/env python3
"""Capture real-world context into a workspace inbox, provenance intact.

One capture = one small markdown file with YAML-ish frontmatter (when, how,
where from, checksums) landing in `<workspace>/inbox/` — or `capture/inbox/`
when no workspace was chosen yet. Binary payloads (photos, PDFs, any file)
go to `media/<workspace>/` and the inbox item points at them. Nothing here
touches STATUS/DECISIONS/etc.: an inbox item is STAGED context; it becomes
accepted state only when a session incorporates it (see the "Inbox" section
of each workspace's AGENTS.md).

Used three ways:
  - CLI on the Mac:      capture.py add --ws tokyo-trip --text "..." [--sync]
  - the phone hub:       an optional companion hub server (not included) imports capture_add() for share-sheet
    captures (Android Web Share Target)
  - any agent session:   same CLI, e.g. when snapshotting an email

Stdlib only — must run under plain python3 from any agent, no venv needed.
"""

from __future__ import annotations

import argparse
import hashlib
import html.parser
import json
import re
import subprocess
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import NoReturn

HOME = Path.home()
REPO = HOME / "ai-workspaces"
REGISTRY_PATH = REPO / "registry.json"
UNSORTED_DIR = REPO / "capture" / "inbox"
MEDIA_DIR = REPO / "media"
SYNC_SCRIPT = Path(__file__).resolve().parent / "sync.py"
URL_RE = re.compile(r"^https?://\S+$")
FETCH_TIMEOUT_S = 15
EXTRACT_LIMIT_CHARS = 6000
SLUG_LIMIT = 40


def fail(message: str) -> NoReturn:
    print(f"error: {message}", file=sys.stderr)
    sys.exit(1)


def workspace_names() -> set[str]:
    """Non-archived workspaces from the registry."""
    try:
        raw = json.loads(REGISTRY_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return set()
    return {
        name
        for name, entry in raw.get("workspaces", {}).items()
        if isinstance(entry, dict) and entry.get("status") != "archived"
    }


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:SLUG_LIMIT].rstrip("-") or "capture"


class _TextExtractor(html.parser.HTMLParser):
    """Readable-text extraction: drop script/style/nav noise, keep prose."""

    SKIP = {"script", "style", "noscript", "svg", "header", "footer", "nav"}

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.title = ""
        self._skip_depth = 0
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag in self.SKIP:
            self._skip_depth += 1
        if tag == "title":
            self._in_title = True
        if tag in {"p", "br", "div", "li", "tr", "h1", "h2", "h3", "h4"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self.SKIP and self._skip_depth:
            self._skip_depth -= 1
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title and not self.title:
            self.title = data.strip()
        if not self._skip_depth and data.strip():
            self.parts.append(data)


def fetch_url_extract(url: str) -> tuple[str, str]:
    """(title, readable text extract) for a URL; empty strings on failure.

    The extract is the durable copy — the page may die, the capture won't.
    """
    request = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (workspace-capture)"}
    )
    try:
        with urllib.request.urlopen(request, timeout=FETCH_TIMEOUT_S) as resp:
            if "html" not in (resp.headers.get("Content-Type") or ""):
                return "", ""
            raw = resp.read(1_500_000)
    except (OSError, ValueError):
        return "", ""
    extractor = _TextExtractor()
    try:
        extractor.feed(raw.decode("utf-8", errors="replace"))
    except Exception:  # noqa: BLE001 — malformed HTML must never kill a capture
        return "", ""
    text = re.sub(r"\n{3,}", "\n\n", " ".join(extractor.parts).replace(" \n ", "\n"))
    text = re.sub(r"[ \t]{2,}", " ", text).strip()
    return extractor.title, text[:EXTRACT_LIMIT_CHARS]


def _frontmatter(fields: dict[str, str]) -> str:
    lines = ["---"]
    for key, value in fields.items():
        if value:
            lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines)


def capture_add(
    *,
    workspace: str | None,
    text: str = "",
    url: str = "",
    title: str = "",
    file_name: str = "",
    file_bytes: bytes | None = None,
    file_path: str = "",
    source: str = "cli",
    via: str = "",
    fetch: bool = True,
) -> Path:
    """Write one capture; returns the inbox item path.

    Args:
        workspace: target workspace name, or None for capture/inbox (unsorted).
        text: note / shared text / page extract.
        url: source URL when the capture is (or came from) a link.
        title: human title; derived from content when empty.
        file_name: original filename for a binary payload.
        file_bytes: binary payload content (exclusive with file_path).
        file_path: path to a file on disk to copy in (exclusive with file_bytes).
        source: how it arrived (android-share, cli, email, hub-chat, …).
        via: device/agent that sent it.
        fetch: fetch a readable extract for bare-URL captures.

    Raises:
        ValueError: unknown workspace, or nothing to capture.
    """
    names = workspace_names()
    if workspace and workspace not in names:
        raise ValueError(f"unknown workspace {workspace!r}")
    if not (text.strip() or url.strip() or file_bytes or file_path):
        raise ValueError("nothing to capture")

    # A shared "text" that is actually just a link is a URL capture.
    if not url and URL_RE.match(text.strip()):
        url, text = text.strip(), ""

    extract = ""
    if url and fetch and not text:
        fetched_title, extract = fetch_url_extract(url)
        title = title or fetched_title

    now = datetime.now().astimezone()
    stamp = now.strftime("%Y-%m-%d-%H%M%S")
    media_ref = ""
    sha = ""

    payload: bytes | None = None
    if file_path:
        src = Path(file_path).expanduser()
        if not src.is_file():
            raise ValueError(f"no such file: {src}")
        payload = src.read_bytes()
        file_name = file_name or src.name
    elif file_bytes is not None:
        payload = file_bytes
        file_name = file_name or "payload.bin"

    if payload is not None:
        sha = hashlib.sha256(payload).hexdigest()
        safe = re.sub(r"[^A-Za-z0-9._-]", "_", file_name).strip("._") or "payload"
        media_dir = MEDIA_DIR / (workspace or "_unsorted")
        media_dir.mkdir(parents=True, exist_ok=True)
        media_path = media_dir / f"{stamp}_{safe}"
        media_path.write_bytes(payload)
        media_ref = str(media_path.relative_to(REPO))

    title = title or (text.strip().splitlines()[0][:60] if text.strip() else "")
    title = title or (url if url else file_name) or "capture"

    inbox_dir = (REPO / workspace / "inbox") if workspace else UNSORTED_DIR
    inbox_dir.mkdir(parents=True, exist_ok=True)
    item = inbox_dir / f"{stamp}_{slugify(title)}.md"

    kind = "file" if media_ref else ("url" if url else "text")
    front = _frontmatter(
        {
            "captured": now.isoformat(timespec="seconds"),
            "type": kind,
            "source": source,
            "via": via,
            "url": url,
            "media": media_ref,
            "sha256": sha,
            "original_name": file_name if media_ref else "",
        }
    )
    body_parts = [f"# {title}", ""]
    if text.strip():
        body_parts += [text.strip(), ""]
    if extract:
        body_parts += ["## Page extract (fetched at capture time)", "", extract, ""]
    if media_ref:
        body_parts += [f"Payload: `{media_ref}` (sha256 {sha[:12]}…)", ""]
    item.write_text(front + "\n\n" + "\n".join(body_parts))
    return item


def inbox_items(workspace: str | None = None) -> list[Path]:
    """Pending inbox items — one workspace's, or every inbox in the repo."""
    if workspace:
        return sorted((REPO / workspace / "inbox").glob("*.md"))
    items = sorted(UNSORTED_DIR.glob("*.md"))
    for name in sorted(workspace_names()):
        items += sorted((REPO / name / "inbox").glob("*.md"))
    return items


def run_sync() -> int:
    proc = subprocess.run(
        [sys.executable, str(SYNC_SCRIPT), "now"], capture_output=True, text=True
    )
    tail = (proc.stdout.strip() or proc.stderr.strip()).splitlines()
    if tail:
        print(tail[-1])
    return proc.returncode


def cmd_add(args: argparse.Namespace) -> None:
    text = args.text or ""
    if text == "-":
        text = sys.stdin.read()
    try:
        item = capture_add(
            workspace=args.ws,
            text=text,
            url=args.url or "",
            title=args.title or "",
            file_path=args.file or "",
            source=args.source,
            via=args.via,
            fetch=not args.no_fetch,
        )
    except ValueError as exc:
        fail(str(exc))
    print(f"captured: {item.relative_to(REPO)}")
    if args.sync:
        run_sync()


def cmd_list(args: argparse.Namespace) -> None:
    items = inbox_items(args.ws)
    if not items:
        print("inbox empty")
        return
    for item in items:
        rel = item.relative_to(REPO)
        first = item.read_text().split("---", 2)[-1].strip().splitlines()
        print(f"{rel}  —  {first[0].lstrip('# ') if first else ''}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="capture.py",
        description="Capture context into a workspace inbox (provenance intact).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="capture text, a URL, or a file")
    p_add.add_argument("--ws", default=None, help="target workspace (else unsorted)")
    p_add.add_argument("--text", default=None, help="note text; '-' reads stdin")
    p_add.add_argument("--url", default=None, help="source URL")
    p_add.add_argument("--title", default=None)
    p_add.add_argument("--file", default=None, help="file to copy into media/")
    p_add.add_argument("--source", default="cli", help="how this arrived")
    p_add.add_argument("--via", default="", help="device/agent")
    p_add.add_argument("--no-fetch", action="store_true", help="skip URL extract")
    p_add.add_argument("--sync", action="store_true", help="run sync.py after")
    p_add.set_defaults(func=cmd_add)

    p_list = sub.add_parser("list", help="list pending inbox items")
    p_list.add_argument("--ws", default=None)
    p_list.set_defaults(func=cmd_list)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
