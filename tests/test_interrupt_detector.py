"""Test InterruptDetector."""

import unittest

from adapters.interrupt.detector import (
    is_lane_executing,
    build_interrupt_context,
    should_enter_interrupt_routing,
)


class InterruptDetectorTest(unittest.TestCase):
    def test_is_lane_executing_active(self):
        self.assertTrue(is_lane_executing("active"))

    def test_is_lane_executing_in_progress(self):
        self.assertTrue(is_lane_executing("in_progress"))

    def test_is_lane_executing_executing(self):
        self.assertTrue(is_lane_executing("executing"))

    def test_is_lane_executing_none(self):
        self.assertFalse(is_lane_executing(None))

    def test_is_lane_executing_empty(self):
        self.assertFalse(is_lane_executing(""))

    def test_is_lane_executing_unknown(self):
        self.assertFalse(is_lane_executing("merged"))

    def test_build_interrupt_context(self):
        ctx = build_interrupt_context(
            current_state="EXECUTE",
            current_milestone="test-milestone",
            current_lane="test-lane",
            current_work_unit="WU-001",
            lane_status="active",
            lane_wu_counts={"pending": 2, "done": 1},
        )
        self.assertEqual(ctx.current_state, "EXECUTE")
        self.assertEqual(ctx.current_lane, "test-lane")
        self.assertEqual(ctx.lane_wu_counts, {"pending": 2, "done": 1})

    def test_should_enter_interrupt_routing_chat(self):
        self.assertFalse(should_enter_interrupt_routing("EXECUTE", "active", "chat"))

    def test_should_enter_interrupt_routing_trivial(self):
        self.assertFalse(should_enter_interrupt_routing("EXECUTE", "active", "trivial"))

    def test_should_enter_interrupt_routing_small_plus_active_lane(self):
        self.assertTrue(should_enter_interrupt_routing("EXECUTE", "active", "Small+"))

    def test_should_enter_interrupt_routing_no_lane(self):
        self.assertFalse(should_enter_interrupt_routing("EXECUTE", None, "Small+"))

    def test_should_enter_interrupt_routing_complete_state(self):
        self.assertFalse(should_enter_interrupt_routing("COMPLETE", "active", "Small+"))

    def test_should_enter_interrupt_routing_read_context(self):
        self.assertFalse(should_enter_interrupt_routing("READ_CONTEXT", "active", "Small+"))


if __name__ == "__main__":
    unittest.main()
