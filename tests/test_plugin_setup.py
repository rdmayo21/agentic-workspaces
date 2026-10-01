"""Verify actual setup and project lifecycle in an isolated user's home."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SETUP = ROOT / "skills/new-ai-workspace/scripts/setup.py"


class PluginSetupTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.env = dict(os.environ, HOME=str(self.home), GIT_CONFIG_GLOBAL=os.devnull,
                        GIT_CONFIG_NOSYSTEM="1", PYTHONDONTWRITEBYTECODE="1")
        # Exercise Gemini wiring without touching the real user's installation.
        (self.home / ".gemini").mkdir()

    def run_script(self, path, *args, success=True):
        result = subprocess.run([sys.executable, str(path), *args], env=self.env,
                                cwd=self.home, capture_output=True, text=True)
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
        return result

    def snapshot(self):
        return {str(p.relative_to(self.home)): ("link", os.readlink(p)) if p.is_symlink()
                else ("file", p.read_bytes()) for p in self.home.rglob("*")
                if p.is_symlink() or p.is_file()}

    def test_setup_lifecycle_and_existing_store_preservation(self):
        self.run_script(SETUP)
        store = self.home / "ai-workspaces"
        scripts = store / "skills/new-ai-workspace/scripts"
        self.assertTrue((store / ".git").is_dir())
        self.assertEqual(subprocess.check_output(["git", "-C", str(store), "remote"], env=self.env), b"")
        self.assertEqual((self.home / ".agents/skills/new-ai-workspace").resolve(),
                         (store / "skills/new-ai-workspace").resolve())
        self.assertTrue((self.home / ".gemini/commands/new-ai-workspace.toml").is_file())
        self.run_script(scripts / "workspace.py", "create", "lisbon-trip", "--type", "travel",
                        "--description", "Plan a fictional trip.",
                        "--skill-description", "Lisbon trip: flights, lodging, and day plans.")
        self.assertTrue((store / "lisbon-trip/BOOKINGS.md").is_file())
        self.run_script(scripts / "capture.py", "add", "--ws", "lisbon-trip", "--text", "Choose dates.")
        self.assertEqual(len(list((store / "lisbon-trip/inbox").glob("*.md"))), 1)
        self.run_script(scripts / "sync.py", "now")
        self.assertTrue(subprocess.check_output(["git", "-C", str(store), "log", "-1", "--oneline"], env=self.env))
        self.run_script(scripts / "workspace.py", "archive", "lisbon-trip")
        self.assertTrue((store / "lisbon-trip/STATUS.md").is_file())
        self.assertEqual(json.loads((store / "registry.json").read_text())["workspaces"]["lisbon-trip"]["status"], "archived")
        before = self.snapshot()
        self.run_script(SETUP)
        self.assertEqual(before, self.snapshot(), "setup modified an existing workspace system")

    def test_unrelated_existing_directory_is_untouched(self):
        store = self.home / "ai-workspaces"
        store.mkdir()
        (store / "important.txt").write_text("Keep this.")
        before = self.snapshot()
        self.run_script(SETUP, success=False)
        self.assertEqual(before, self.snapshot())

    def test_conflicting_skill_store_is_untouched(self):
        (self.home / ".ai/skills").mkdir(parents=True)
        (self.home / ".ai/skills/private.txt").write_text("Keep this too.")
        before = self.snapshot()
        self.run_script(SETUP, success=False)
        self.assertEqual(before, self.snapshot())


if __name__ == "__main__":
    unittest.main()
