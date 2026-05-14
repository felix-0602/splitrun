"""Integration test: detector -> classifier -> router -> reconciler pipeline."""

import unittest

from adapters.interrupt.detector import should_enter_interrupt_routing
from adapters.interrupt.classifier import normalize_intent
from adapters.interrupt.router import route
from adapters.interrupt.schemas import (
    InterruptContext,
    RouteType,
)


class InterruptIntegrationTest(unittest.TestCase):
    def test_full_pipeline_cache_answer(self):
        """User asks a simple question while lane is executing."""
        self.assertTrue(should_enter_interrupt_routing("EXECUTE", "active", "Small+"))

        intent = normalize_intent("what is the port number?")
        self.assertEqual(intent.route_type, RouteType.CACHE_ANSWER)

        ctx = InterruptContext(
            current_state="EXECUTE",
            current_lane="main",
            lane_status="active",
        )
        decision = route(intent, ctx)
        self.assertEqual(decision.route_type, RouteType.CACHE_ANSWER)
        self.assertFalse(decision.should_pause_lane)

    def test_full_pipeline_new_lane(self):
        """User requests a complex new feature."""
        self.assertTrue(should_enter_interrupt_routing("EXECUTE", "active", "Small+"))

        intent = normalize_intent(
            "implement a new authentication system with OAuth2 and JWT"
        )
        self.assertEqual(intent.route_type, RouteType.NEW_LANE_LONG_TASK)

        ctx = InterruptContext(
            current_state="EXECUTE",
            current_milestone="test",
            current_lane="main",
            current_work_unit="WU-001",
            lane_status="active",
        )
        decision = route(intent, ctx)
        self.assertEqual(decision.route_type, RouteType.NEW_LANE_LONG_TASK)
        self.assertTrue(decision.should_pause_lane)
        self.assertIsNotNone(decision.new_lane_name)
        self.assertIsNotNone(decision.handoff_payload)

    def test_no_interrupt_when_no_lane(self):
        """No interrupt routing when no lane is executing."""
        self.assertFalse(should_enter_interrupt_routing("READ_CONTEXT", None, "Small+"))

    def test_classify_then_route_modify_plan(self):
        """User modifies current plan mid-execution."""
        intent = normalize_intent("actually change the login to use email instead")
        ctx = InterruptContext(current_state="EXECUTE", lane_status="active")

        decision = route(intent, ctx)
        self.assertEqual(decision.route_type, RouteType.MODIFY_CURRENT_PLAN)
        self.assertTrue(decision.should_pause_lane)
        self.assertIsNotNone(decision.plan_amendment)


if __name__ == "__main__":
    unittest.main()
