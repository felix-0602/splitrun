"""Test Reconciler — all 5 outcomes + clear_interrupt."""

import json
import tempfile
import unittest
from pathlib import Path

from adapters.interrupt.reconciler import reconcile, clear_interrupt
from adapters.interrupt.schemas import ReconciliationOutcome


class ReconcilerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / ".deepship").mkdir()
        self.state_path = self.root / ".deepship" / "state.json"
        self.state_path.write_text(json.dumps({
            "current_state": "EXECUTE",
            "current_work_unit": "WU-001",
            "_interrupt_pending": True,
        }))

    def tearDown(self):
        self.tmp.cleanup()

    def _read_state(self):
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def test_continue_clears_pending(self):
        result = reconcile(
            ReconciliationOutcome.CONTINUE,
            "test-lane", "EXECUTE", self.root,
        )
        state = self._read_state()
        self.assertEqual(state.get("_interrupt_reconciliation"), "continue")

    def test_pause_keeps_pending(self):
        reconcile(
            ReconciliationOutcome.PAUSE,
            "test-lane", "EXECUTE", self.root,
        )
        state = self._read_state()
        self.assertEqual(state.get("_interrupt_pending"), True)
        self.assertEqual(state.get("_interrupt_reconciliation"), "pause")

    def test_superseded(self):
        reconcile(
            ReconciliationOutcome.SUPERSEDED,
            "test-lane", "EXECUTE", self.root,
        )
        state = self._read_state()
        self.assertEqual(state.get("_interrupt_reconciliation"), "superseded")

    def test_plan_updated(self):
        reconcile(
            ReconciliationOutcome.PLAN_UPDATED,
            "test-lane", "EXECUTE", self.root,
        )
        state = self._read_state()
        self.assertEqual(state.get("_interrupt_reconciliation"), "plan_updated")

    def test_delegated(self):
        reconcile(
            ReconciliationOutcome.DELEGATED,
            "test-lane", "EXECUTE", self.root,
        )
        state = self._read_state()
        self.assertEqual(state.get("_interrupt_reconciliation"), "delegated")
        self.assertEqual(state.get("_interrupt_pending"), True)

    def test_clear_interrupt_removes_all_flags(self):
        self.state_path.write_text(json.dumps({
            "current_state": "EXECUTE",
            "_interrupt_pending": True,
            "_interrupt_type": "NEW_LANE_LONG_TASK",
            "_interrupted_lane": "test-lane",
            "_interrupt_intent": "test intent",
        }))
        result = clear_interrupt(self.root)
        state = self._read_state()
        self.assertNotIn("_interrupt_pending", state)
        self.assertNotIn("_interrupt_type", state)
        self.assertNotIn("_interrupted_lane", state)
        self.assertEqual(result.outcome, ReconciliationOutcome.CONTINUE)


if __name__ == "__main__":
    unittest.main()
