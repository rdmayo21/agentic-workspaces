#!/usr/bin/env python3
"""Initialize a workspace store from an installed plugin without cloning it.

Standard library only. No downloads, remote configuration, push, or overwrite
of an existing store. Run only when the user has requested workspace setup.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def main() -> int:
    if sys.version_info < (3, 11):
        print("error: Python 3.11 or newer is required", file=sys.stderr)
        return 1
    root = Path.home() / "ai-workspaces"
    source = Path(__file__).resolve().parent.parent
    target = root / "skills" / "new-ai-workspace"
    if root.exists() or root.is_symlink():
        if (target / "SKILL.md").is_file():
            print(f"Existing workspace store: {root}")
            print("Preserved all files and agent wiring; use its existing instructions and scripts.")
            return 0
        print(f"error: {root} already exists; inspect it before setup (nothing changed)", file=sys.stderr)
        return 1
    if shutil.which("git") is None:
        print("error: Git is required", file=sys.stderr)
        return 1
    # bootstrap would otherwise fail after partly changing the store.
    compat = Path.home() / ".ai" / "skills"
    if compat.exists() and not compat.is_symlink():
        print(f"error: {compat} is a real directory; reconcile it before setup (nothing changed)", file=sys.stderr)
        return 1
    if compat.is_symlink() and compat.resolve() != (root / "skills").resolve():
        print(f"error: {compat} points to another store; reconcile it before setup (nothing changed)", file=sys.stderr)
        return 1

    target.parent.mkdir(parents=True)
    shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"))
    (root / ".gitignore").write_text("__pycache__/\n.DS_Store\n.tmp/\n")
    license_path = source.parent.parent / "LICENSE"
    if license_path.is_file():
        shutil.copy2(license_path, root / "LICENSE")
    subprocess.run(["git", "init", "--initial-branch=main", str(root)], check=True)
    subprocess.run([sys.executable, str(target / "scripts" / "workspace.py"), "bootstrap"], check=True)
    print(f"Ready: {root}")
    print("No remote is configured. Add only a private remote before enabling backup.")
    print("Restart agent sessions to discover new pointer skills.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
