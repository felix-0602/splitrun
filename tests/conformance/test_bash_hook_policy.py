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


def run_write_hook(cwd: Path, target: Path):
    payload = {
        "tool_name": "Write",
        "cwd": str(cwd),
        "tool_input": {"file_path": str(target)},
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

    def test_code_write_blocked_when_session_owner_differs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".deepship").mkdir()
            (root / "src").mkdir()
            (root / ".deepship" / "state.json").write_text(
                json.dumps({"current_state": "EXECUTE", "current_work_unit": "WU-001"}),
                encoding="utf-8",
            )
            (root / ".deepship" / "work_units.json").write_text(
                json.dumps({"work_units": [{"id": "WU-001", "files_allowed": ["src/a.py"]}]}),
                encoding="utf-8",
            )
            (root / ".deepship" / "session.json").write_text(
                json.dumps({"owner_worktree": str((root / "other").resolve())}),
                encoding="utf-8",
            )

            result = run_write_hook(root, root / "src" / "a.py")

            self.assertIn("permissionDecision", result.stdout)
            self.assertIn("deny", result.stdout)
            self.assertIn("not session owner", result.stdout)

    def test_plan_step_allows_dynamic_planning_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".deepship" / "plan-revisions").mkdir(parents=True)
            (root / ".deepship" / "a2a").mkdir()
            (root / ".deepship" / "prompt-supplements").mkdir()
            (root / ".deepship" / "state.json").write_text(
                json.dumps({"current_state": "PLAN_STEP"}),
                encoding="utf-8",
            )
            (root / ".deepship" / "work_units.json").write_text(
                json.dumps({"work_units": []}),
                encoding="utf-8",
            )

            targets = [
                root / ".deepship" / "plan-revisions" / "plan-2.md",
                root / ".deepship" / "a2a" / "handoff-1.json",
                root / ".deepship" / "prompt-supplements" / "handoff-1.md",
                root / ".deepship" / "sessions.json",
            ]

            for target in targets:
                result = run_write_hook(root, target)
                self.assertNotIn("permissionDecision", result.stdout, str(target))

    def test_execute_blocks_dynamic_planning_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".deepship" / "a2a").mkdir(parents=True)
            (root / ".deepship" / "state.json").write_text(
                json.dumps({"current_state": "EXECUTE", "current_work_unit": "WU-001"}),
                encoding="utf-8",
            )
            (root / ".deepship" / "work_units.json").write_text(
                json.dumps({"work_units": [{"id": "WU-001", "files_allowed": ["src/a.py"]}]}),
                encoding="utf-8",
            )

            result = run_write_hook(root, root / ".deepship" / "a2a" / "handoff-1.json")

            self.assertIn("permissionDecision", result.stdout)
            self.assertIn("deny", result.stdout)


if __name__ == "__main__":
    unittest.main()
