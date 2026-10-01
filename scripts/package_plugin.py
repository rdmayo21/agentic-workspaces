#!/usr/bin/env python3
"""Build a minimal public plugin ZIP from an explicit source allowlist."""

from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    manifest = json.loads((ROOT / "plugin.json").read_text())
    interface = manifest["extensions"]["com.openai"]["interface"]
    for field, limit in (("displayName", 30), ("shortDescription", 30), ("longDescription", 4000)):
        assert 0 < len(interface[field]) <= limit, f"Invalid {field}"
    for prompt in interface["defaultPrompt"]:
        assert 0 < len(prompt) <= 128, "Invalid starter prompt"
    assert len(interface["defaultPrompt"]) <= 3
    paths = [ROOT / name for name in ("plugin.json", "LICENSE", "PRIVACY.md", "README.md")]
    for directory in ("assets", "skills/new-ai-workspace"):
        paths.extend(p for p in (ROOT / directory).rglob("*") if p.is_file() and not p.is_symlink()
                     and "__pycache__" not in p.parts and p.suffix != ".pyc" and p.name != ".DS_Store")
    included = {p.relative_to(ROOT).as_posix() for p in paths}
    for field in ("composerIcon", "composerIconDark", "logo", "logoDark"):
        assert interface[field].removeprefix("./") in included, f"Missing {field}"
    onboarding = manifest["extensions"]["com.openai"]["onboardingSkill"]
    assert onboarding.removeprefix("./") in included, "Missing onboarding skill"
    destination = ROOT / "dist" / f"{manifest['name']}-{manifest['version']}.zip"
    destination.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(paths):
            assert path.resolve().is_relative_to(ROOT), f"Outside package: {path}"
            archive.write(path, path.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(destination) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist()) == included
    print(f"{destination} ({len(paths)} files, {destination.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
