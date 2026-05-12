import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


HOOK_PATH = Path.home() / ".claude" / "hooks" / "deepship-policy-guard.js"


def run_hook(cwd: Path, target: Path, trusted_roots=None):
    env = os.environ.copy()
    if trusted_roots:
        env["DEEPSHIP_TRUSTED_WRITE_ROOTS"] = os.pathsep.join(str(p) for p in trusted_roots)

    payload = {
        "tool_name": "Write",
        "cwd": str(cwd),
        "tool_input": {"file_path": str(target), "content": "x"},
    }
    return subprocess.run(
        ["node", str(HOOK_PATH)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env=env,
        timeout=5,
        check=False,
    )


class GlobalDeepShipPolicyGuardTest(unittest.TestCase):
    def test_trusted_write_root_allows_dogfood_runtime_edits(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "app"
            trusted = Path(tmp) / "mate"
            (root / ".deepship").mkdir(parents=True)
            (trusted / "tools").mkdir(parents=True)
            (root / ".deepship" / "state.json").write_text(
                json.dumps({"current_state": "EXECUTE", "current_work_unit": "WU-001"}),
                encoding="utf-8",
            )
            (root / ".deepship" / "work_units.json").write_text(
                json.dumps({"work_units": [{"id": "WU-001", "files_allowed": ["src/a.py"]}]}),
                encoding="utf-8",
            )

            result = run_hook(root, trusted / "tools" / "bash_tool.py", [trusted])

            self.assertNotIn("permissionDecision", result.stdout)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_untrusted_external_write_still_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "app"
            outside = Path(tmp) / "outside"
            (root / ".deepship").mkdir(parents=True)
            outside.mkdir(parents=True)
            (root / ".deepship" / "state.json").write_text(
                json.dumps({"current_state": "EXECUTE", "current_work_unit": "WU-001"}),
                encoding="utf-8",
            )
            (root / ".deepship" / "work_units.json").write_text(
                json.dumps({"work_units": [{"id": "WU-001", "files_allowed": ["src/a.py"]}]}),
                encoding="utf-8",
            )

            result = run_hook(root, outside / "other.py")

            self.assertIn("permissionDecision", result.stdout)
            self.assertIn("deny", result.stdout)


if __name__ == "__main__":
    unittest.main()
