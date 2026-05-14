"""Test rotate enforcement gates."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from adapters.cc import transition_state


class RotateEnforcementTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / ".deepship").mkdir()
        self.state_path = self.root / ".deepship" / "state.json"
        self.wu_path = self.root / ".deepship" / "work_units.json"
        self._write_state({"current_state": "PLAN_STEP", "_session_wu_count": 0})
        self._write_wus([
            {"id": "WU-T01", "status": "pending", "files_allowed": ["test.py"],
             "execution_mode": "inline", "risk_level": "low", "owner": "orchestrator"},
            {"id": "WU-T02", "status": "pending", "files_allowed": ["test2.py"],
             "execution_mode": "inline", "risk_level": "low", "owner": "orchestrator"},
            {"id": "WU-T03", "status": "pending", "files_allowed": ["test3.py"],
             "execution_mode": "inline", "risk_level": "low", "owner": "orchestrator"},
        ])

    def tearDown(self):
        self.tmp.cleanup()

    def _write_state(self, d):
        self.state_path.write_text(json.dumps(d), encoding="utf-8")

    def _write_wus(self, wus):
        self.wu_path.write_text(json.dumps(
            {"milestone": "test", "work_units": wus},
            indent=2,
        ), encoding="utf-8")

    def test_session_wu_count_blocks_at_six(self):
        """_session_wu_count >= 6 with remaining pending WUs → blocked."""
        self._write_state({
            "current_state": "PLAN_STEP",
            "_session_wu_count": 6,
            "current_work_unit": "WU-T02",
        })

        result = transition_state.transition("EXECUTE", wu_id="WU-T03", project_root=self.root)
        self.assertFalse(result["success"], f"Expected block, got: {result}")
        self.assertIn("rotate", result["reason"])

    def test_session_wu_count_allows_when_no_remaining(self):
        """_session_wu_count >= 6 but no other pending WUs → allowed."""
        self._write_state({
            "current_state": "PLAN_STEP",
            "_session_wu_count": 6,
            "current_work_unit": "WU-T02",
        })
        self._write_wus([
            {"id": "WU-T01", "status": "integrated", "files_allowed": ["test.py"],
             "execution_mode": "inline", "risk_level": "low", "owner": "orchestrator"},
            {"id": "WU-T02", "status": "integrated", "files_allowed": ["test2.py"],
             "execution_mode": "inline", "risk_level": "low", "owner": "orchestrator"},
            {"id": "WU-T03", "status": "pending", "files_allowed": ["test3.py"],
             "execution_mode": "inline", "risk_level": "low", "owner": "orchestrator"},
        ])

        result = transition_state.transition("EXECUTE", wu_id="WU-T03", project_root=self.root)
        self.assertTrue(result["success"], f"Expected allow, got: {result}")

    def test_session_wu_count_allows_below_six(self):
        """_session_wu_count = 5 → allowed (below threshold)."""
        self._write_state({
            "current_state": "PLAN_STEP",
            "_session_wu_count": 5,
            "current_work_unit": "WU-T01",
        })

        result = transition_state.transition("EXECUTE", wu_id="WU-T02", project_root=self.root)
        self.assertTrue(result["success"], f"Expected allow, got: {result}")

    @patch("adapters.cc.transition_state._is_context_critical", return_value=True)
    def test_context_critical_blocks_execute(self, mock_ctx):
        """_is_context_critical returns True → blocked."""
        self._write_state({
            "current_state": "PLAN_STEP",
            "_session_wu_count": 0,
            "current_work_unit": "WU-T01",
        })

        result = transition_state.transition("EXECUTE", wu_id="WU-T01", project_root=self.root)
        self.assertFalse(result["success"], f"Expected block, got: {result}")
        self.assertIn("上下文", result["reason"])

    def test_milestone_archive_on_complete(self):
        """COMPLETE archives work_units.json to .deepship/archive/."""
        self._write_state({
            "current_state": "ADVANCE",
            "_session_wu_count": 2,
            "current_milestone": "test-milestone",
            "current_work_unit": "WU-T03",
        })
        self._write_wus([
            {"id": "WU-T01", "status": "integrated", "files_allowed": ["test.py"],
             "execution_mode": "inline", "risk_level": "low", "owner": "orchestrator"},
        ])

        result = transition_state.transition("COMPLETE", project_root=self.root)
        self.assertTrue(result["success"], f"Expected success, got: {result}")

        archive = self.root / ".deepship" / "archive"
        files = list(archive.glob("milestone-*.json"))
        self.assertEqual(len(files), 1, f"Expected 1 archive file, got: {files}")
        self.assertIn("test-milestone", files[0].name)

    def test_clear_rotation_resets_counter(self):
        """--clear-rotation resets _session_wu_count to 0."""
        self._write_state({
            "current_state": "READ_CONTEXT",
            "_session_wu_count": 5,
            "_rotation_pending": True,
            "_rotated_at": "2026-01-01T00:00:00Z",
            "_rotated_from_wu": "WU-001",
        })

        result = transition_state.transition(
            "READ_CONTEXT", project_root=self.root, clear_rotation=True
        )
        self.assertTrue(result["success"])
        state = json.loads(self.state_path.read_text(encoding="utf-8"))
        self.assertEqual(state.get("_session_wu_count"), 0)
        self.assertNotIn("_rotation_pending", state)


if __name__ == "__main__":
    unittest.main()
