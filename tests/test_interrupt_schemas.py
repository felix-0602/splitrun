"""Test interrupt routing data structures."""

import unittest

from adapters.interrupt.schemas import (
    RouteType,
    ReconciliationOutcome,
    InterruptContext,
    NormalizedIntent,
    A2AHandoffPayload,
    RouteDecision,
    ReconciliationResult,
)


class InterruptSchemasTest(unittest.TestCase):
    def test_route_type_values(self):
        self.assertEqual(RouteType.CACHE_ANSWER.value, "CACHE_ANSWER")
        self.assertEqual(RouteType.SMALL_CONTEXT_TASK.value, "SMALL_CONTEXT_TASK")
        self.assertEqual(RouteType.NEW_LANE_LONG_TASK.value, "NEW_LANE_LONG_TASK")
        self.assertEqual(RouteType.MODIFY_CURRENT_PLAN.value, "MODIFY_CURRENT_PLAN")

    def test_reconciliation_outcome_values(self):
        self.assertEqual(ReconciliationOutcome.CONTINUE.value, "continue")
        self.assertEqual(ReconciliationOutcome.PAUSE.value, "pause")
        self.assertEqual(ReconciliationOutcome.SUPERSEDED.value, "superseded")
        self.assertEqual(ReconciliationOutcome.PLAN_UPDATED.value, "plan_updated")
        self.assertEqual(ReconciliationOutcome.DELEGATED.value, "delegated")

    def test_interrupt_context_defaults(self):
        ctx = InterruptContext(current_state="EXECUTE")
        self.assertEqual(ctx.current_state, "EXECUTE")
        self.assertEqual(ctx.current_milestone, "")
        self.assertIsNone(ctx.current_lane)
        self.assertTrue(ctx.interrupted_at)

    def test_normalized_intent_construction(self):
        intent = NormalizedIntent(
            raw_input="fix typo in README",
            summary="Fix a typo in README",
            route_type=RouteType.SMALL_CONTEXT_TASK,
            confidence=0.85,
        )
        self.assertEqual(intent.raw_input, "fix typo in README")
        self.assertFalse(intent.replaces_current_goal)
        self.assertFalse(intent.supplements_current_goal)

    def test_a2a_handoff_roundtrip(self):
        payload = A2AHandoffPayload(
            original_input="test request",
            normalized_intent_summary="test intent",
            lane_summary="test lane",
            plan_summary="test plan",
            constraints=("don't modify X",),
            expected_output="result",
            should_not_do=("don't delete",),
        )
        d = payload.to_dict()
        restored = A2AHandoffPayload.from_dict(d)
        self.assertEqual(restored.original_input, payload.original_input)
        self.assertEqual(restored.normalized_intent_summary, payload.normalized_intent_summary)
        self.assertEqual(restored.constraints, payload.constraints)

    def test_route_decision_all_fields(self):
        d = RouteDecision(
            route_type=RouteType.CACHE_ANSWER,
            should_pause_lane=False,
            summary="direct answer",
        )
        self.assertIsNone(d.handoff_payload)
        self.assertIsNone(d.new_lane_name)

    def test_reconciliation_result_auto_timestamp(self):
        r = ReconciliationResult(
            outcome=ReconciliationOutcome.CONTINUE,
            previous_lane="main",
            previous_state="EXECUTE",
            summary="done",
        )
        self.assertTrue(r.timestamp)


if __name__ == "__main__":
    unittest.main()
