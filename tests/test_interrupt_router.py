"""Test InterruptRouter — routing decisions for all 4 types."""

import unittest

from adapters.interrupt.schemas import (
    InterruptContext,
    NormalizedIntent,
    RouteType,
)
from adapters.interrupt.router import route


class InterruptRouterTest(unittest.TestCase):
    def setUp(self):
        self.ctx = InterruptContext(
            current_state="EXECUTE",
            current_milestone="test-milestone",
            current_lane="test-lane",
            current_work_unit="WU-001",
            lane_status="active",
        )

    def test_cache_answer_route(self):
        intent = NormalizedIntent(
            raw_input="what time is it?",
            summary="time query",
            route_type=RouteType.CACHE_ANSWER,
            confidence=0.9,
        )
        decision = route(intent, self.ctx)
        self.assertEqual(decision.route_type, RouteType.CACHE_ANSWER)
        self.assertFalse(decision.should_pause_lane)
        self.assertIsNone(decision.handoff_payload)

    def test_small_context_task_route(self):
        intent = NormalizedIntent(
            raw_input="find the login function",
            summary="locate login function",
            route_type=RouteType.SMALL_CONTEXT_TASK,
            confidence=0.8,
        )
        decision = route(intent, self.ctx)
        self.assertEqual(decision.route_type, RouteType.SMALL_CONTEXT_TASK)
        self.assertTrue(decision.should_pause_lane)
        self.assertIsNotNone(decision.handoff_payload)

    def test_new_lane_long_task_route(self):
        intent = NormalizedIntent(
            raw_input="implement a new auth module",
            summary="new auth module",
            route_type=RouteType.NEW_LANE_LONG_TASK,
            confidence=0.85,
            keywords=("auth", "module", "implement"),
        )
        decision = route(intent, self.ctx)
        self.assertEqual(decision.route_type, RouteType.NEW_LANE_LONG_TASK)
        self.assertTrue(decision.should_pause_lane)
        self.assertIsNotNone(decision.new_lane_name)
        self.assertIsNotNone(decision.handoff_payload)

    def test_modify_current_plan_route(self):
        intent = NormalizedIntent(
            raw_input="change the button color to red",
            summary="change button color",
            route_type=RouteType.MODIFY_CURRENT_PLAN,
            confidence=0.8,
        )
        decision = route(intent, self.ctx)
        self.assertEqual(decision.route_type, RouteType.MODIFY_CURRENT_PLAN)
        self.assertTrue(decision.should_pause_lane)
        self.assertIsNotNone(decision.plan_amendment)


if __name__ == "__main__":
    unittest.main()
