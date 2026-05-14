import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HOOK_PATH = ROOT / "adapters" / "claude-code" / "hooks" / "deepship-policy-guard.js"


def run_hook(cwd: Path, target: Path, trusted_roots=None, content="x"):
    env = os.environ.copy()
    if trusted_roots:
        env["DEEPSHIP_TRUSTED_WRITE_ROOTS"] = os.pathsep.join(str(p) for p in trusted_roots)

    payload = {
        "tool_name": "Write",
        "cwd": str(cwd),
        "tool_input": {"file_path": str(target), "content": content},
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

    def test_active_lane_work_units_cannot_be_written_to_main_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "app"
            lane = root / ".deepship" / "lanes" / "rotate-smoke"
            lane_home = lane / ".deepship"
            (root / ".deepship").mkdir(parents=True)
            lane_home.mkdir(parents=True)
            (root / ".deepship" / "state.json").write_text(
                json.dumps({"current_state": "EXECUTE", "current_work_unit": "WU-ROOT"}),
                encoding="utf-8",
            )
            (root / ".deepship" / "work_units.json").write_text(
                json.dumps({"work_units": [{"id": "WU-ROOT", "files_allowed": ["src/root.py"]}]}),
                encoding="utf-8",
            )
            (root / ".deepship" / "lanes.json").write_text(
                json.dumps(
                    {
                        "lanes": [
                            {
                                "name": "rotate-smoke",
                                "status": "active",
                                "worktree_path": str(lane),
                                "lane_home": str(lane_home),
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            lane_payload = {
                "milestone": "rotate-smoke-test",
                "work_units": [{"id": "WU-SMOKE-001", "files_allowed": ["src/test_smoke.py"]}],
            }
            (lane_home / "work_units.json").write_text(json.dumps(lane_payload), encoding="utf-8")

            result = run_hook(
                root,
                root / ".deepship" / "work_units.json",
                content=json.dumps(lane_payload),
            )

            self.assertIn("permissionDecision", result.stdout)
            self.assertIn("deny", result.stdout)
            self.assertIn("active lane", result.stdout)

    def test_active_lane_requires_session_owner_before_root_metadata_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "app"
            lane = root / ".deepship" / "lanes" / "rotate-smoke"
            lane_home = lane / ".deepship"
            (root / ".deepship").mkdir(parents=True)
            lane_home.mkdir(parents=True)
            (root / ".deepship" / "state.json").write_text(
                json.dumps({"current_state": "EXECUTE", "current_work_unit": "WU-ROOT"}),
                encoding="utf-8",
            )
            (root / ".deepship" / "work_units.json").write_text(
                json.dumps({"work_units": [{"id": "WU-ROOT", "status": "in_progress", "files_allowed": ["src/root.py"]}]}),
                encoding="utf-8",
            )
            (root / ".deepship" / "lanes.json").write_text(
                json.dumps(
                    {
                        "lanes": [
                            {
                                "name": "rotate-smoke",
                                "status": "active",
                                "worktree_path": str(lane),
                                "lane_home": str(lane_home),
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = run_hook(
                root,
                root / ".deepship" / "state.json",
                content=json.dumps({"current_state": "EXECUTE", "current_work_unit": "WU-ROOT"}),
            )

            self.assertIn("permissionDecision", result.stdout)
            self.assertIn("deny", result.stdout)
            self.assertIn("claim session ownership", result.stdout)

    def test_work_units_status_cannot_jump_from_pending_to_integrated(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "app"
            (root / ".deepship").mkdir(parents=True)
            (root / ".deepship" / "state.json").write_text(
                json.dumps({"current_state": "PLAN_STEP"}),
                encoding="utf-8",
            )
            (root / ".deepship" / "work_units.json").write_text(
                json.dumps({"work_units": [{"id": "WU-001", "status": "pending", "files_allowed": ["src/a.py"]}]}),
                encoding="utf-8",
            )

            result = run_hook(
                root,
                root / ".deepship" / "work_units.json",
                content=json.dumps({"work_units": [{"id": "WU-001", "status": "integrated", "files_allowed": ["src/a.py"]}]}),
            )

            self.assertIn("permissionDecision", result.stdout)
            self.assertIn("deny", result.stdout)
            self.assertIn("illegal WU status transition", result.stdout)

    def test_work_units_replacement_cannot_remove_active_work_unit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "app"
            (root / ".deepship").mkdir(parents=True)
            (root / ".deepship" / "state.json").write_text(
                json.dumps({"current_state": "PLAN_STEP"}),
                encoding="utf-8",
            )
            (root / ".deepship" / "work_units.json").write_text(
                json.dumps(
                    {
                        "work_units": [
                            {"id": "WU-IR02", "status": "in_progress", "files_allowed": ["adapters/interrupt/router.py"]},
                            {"id": "WU-IR03", "status": "integrated", "files_allowed": ["adapters/revolution/detector.py"]},
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = run_hook(
                root,
                root / ".deepship" / "work_units.json",
                content=json.dumps({"work_units": [{"id": "WU-SMOKE-001", "status": "pending", "files_allowed": ["src/test_smoke.py"]}]}),
            )

            self.assertIn("permissionDecision", result.stdout)
            self.assertIn("deny", result.stdout)
            self.assertIn("cannot remove active WU", result.stdout)

    def test_active_lane_state_cannot_be_written_to_main_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "app"
            lane = root / ".deepship" / "lanes" / "rotate-smoke"
            lane_home = lane / ".deepship"
            (root / ".deepship").mkdir(parents=True)
            lane_home.mkdir(parents=True)
            (root / ".deepship" / "state.json").write_text(
                json.dumps({"current_state": "EXECUTE", "current_work_unit": "WU-ROOT"}),
                encoding="utf-8",
            )
            (root / ".deepship" / "work_units.json").write_text(
                json.dumps({"work_units": [{"id": "WU-ROOT", "status": "in_progress", "files_allowed": ["src/root.py"]}]}),
                encoding="utf-8",
            )
            (root / ".deepship" / "session.json").write_text(
                json.dumps({"owner_worktree": str(root.resolve())}),
                encoding="utf-8",
            )
            (root / ".deepship" / "lanes.json").write_text(
                json.dumps(
                    {
                        "lanes": [
                            {
                                "name": "rotate-smoke",
                                "status": "active",
                                "worktree_path": str(lane),
                                "lane_home": str(lane_home),
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            lane_state = {
                "current_state": "READ_CONTEXT",
                "current_milestone": "rotate-smoke-test",
                "current_work_unit": "WU-SMOKE-001",
            }
            (lane_home / "state.json").write_text(json.dumps(lane_state), encoding="utf-8")

            result = run_hook(root, root / ".deepship" / "state.json", content=json.dumps(lane_state))

            self.assertIn("permissionDecision", result.stdout)
            self.assertIn("deny", result.stdout)
            self.assertIn("active lane metadata", result.stdout)

    def test_main_session_cannot_write_active_lane_metadata_directly(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "app"
            lane = root / ".deepship" / "lanes" / "rotate-smoke"
            lane_home = lane / ".deepship"
            (root / ".deepship").mkdir(parents=True)
            lane_home.mkdir(parents=True)
            (root / ".deepship" / "state.json").write_text(
                json.dumps({"current_state": "PLAN_STEP"}),
                encoding="utf-8",
            )
            (root / ".deepship" / "work_units.json").write_text(json.dumps({"work_units": []}), encoding="utf-8")
            (root / ".deepship" / "session.json").write_text(
                json.dumps({"owner_worktree": str(root.resolve())}),
                encoding="utf-8",
            )
            (root / ".deepship" / "lanes.json").write_text(
                json.dumps(
                    {
                        "lanes": [
                            {
                                "name": "rotate-smoke",
                                "status": "active",
                                "worktree_path": str(lane),
                                "lane_home": str(lane_home),
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = run_hook(root, lane_home / "state.json", content=json.dumps({"current_state": "READ_CONTEXT"}))

            self.assertIn("permissionDecision", result.stdout)
            self.assertIn("deny", result.stdout)
            self.assertIn("Open the lane worktree", result.stdout)

    def test_lane_creation_requires_a2a_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "app"
            lane_home = root / ".deepship" / "lanes" / "new-lane" / ".deepship"
            (root / ".deepship").mkdir(parents=True)
            (root / ".deepship" / "state.json").write_text(
                json.dumps({"current_state": "PLAN_STEP"}),
                encoding="utf-8",
            )
            (root / ".deepship" / "work_units.json").write_text(json.dumps({"work_units": []}), encoding="utf-8")

            result = run_hook(root, lane_home / "state.json", content=json.dumps({"current_state": "READ_CONTEXT"}))

            self.assertIn("permissionDecision", result.stdout)
            self.assertIn("deny", result.stdout)
            self.assertIn("A2A contract", result.stdout)


if __name__ == "__main__":
    unittest.main()
