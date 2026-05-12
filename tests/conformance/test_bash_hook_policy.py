import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HOOK_PATH = ROOT / "adapters" / "claude-code" / "hooks" / "deepship-policy-guard.js"


def run_bash_hook(cwd: Path, command: str):
    payload = {
        "tool_name": "Bash",
        "cwd": str(cwd),
        "tool_input": {"command": command},
    }
    return subprocess.run(
        ["node", str(HOOK_PATH)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env=os.environ.copy(),
        timeout=5,
        check=False,
    )


class BashHookPolicyConformance(unittest.TestCase):
    def test_multiline_pipeline_redirect_to_metadata_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".deepship").mkdir()
            (root / ".deepship" / "state.json").write_text(
                json.dumps({"current_state": "EXECUTE", "current_work_unit": "WU-001"}),
                encoding="utf-8",
            )
            (root / ".deepship" / "work_units.json").write_text(
                json.dumps({"work_units": [{"id": "WU-001", "files_allowed": ["src/a.py"]}]}),
                encoding="utf-8",
            )

            result = run_bash_hook(
                root,
                "Get-Content input.json |\n  Set-Content -LiteralPath .deepship/state.json",
            )

            self.assertIn("permissionDecision", result.stdout)
            self.assertIn("deny", result.stdout)


if __name__ == "__main__":
    unittest.main()
