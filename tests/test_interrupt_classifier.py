"""Test IntentClassifier — the most critical routing logic."""

import unittest

from adapters.interrupt.classifier import normalize_intent
from adapters.interrupt.schemas import RouteType


class IntentClassifierTest(unittest.TestCase):
    def test_cache_answer_simple_question(self):
        intent = normalize_intent("what is the port number?")
        self.assertEqual(intent.route_type, RouteType.CACHE_ANSWER)
        self.assertGreaterEqual(intent.confidence, 0.6)

    def test_cache_answer_short_why(self):
        intent = normalize_intent("why did this fail?")
        self.assertEqual(intent.route_type, RouteType.CACHE_ANSWER)

    def test_cache_answer_how_question(self):
        intent = normalize_intent("how does the dispatcher work?")
        self.assertEqual(intent.route_type, RouteType.CACHE_ANSWER)

    def test_small_context_task_find(self):
        intent = normalize_intent("find where the login function is defined")
        self.assertEqual(intent.route_type, RouteType.SMALL_CONTEXT_TASK)

    def test_small_context_task_explain(self):
        intent = normalize_intent("explain the transition_state guard logic")
        self.assertEqual(intent.route_type, RouteType.SMALL_CONTEXT_TASK)

    def test_new_lane_long_task_implement_feature(self):
        intent = normalize_intent(
            "implement a new authentication module with OAuth2 support and database integration"
        )
        self.assertEqual(intent.route_type, RouteType.NEW_LANE_LONG_TASK)

    def test_new_lane_long_task_build_system(self):
        intent = normalize_intent(
            "build a complete CI/CD pipeline with Docker and Kubernetes deployment"
        )
        self.assertEqual(intent.route_type, RouteType.NEW_LANE_LONG_TASK)

    def test_modify_current_plan_instead(self):
        intent = normalize_intent(
            "actually, instead of blue buttons, use red ones and change the layout"
        )
        self.assertEqual(intent.route_type, RouteType.MODIFY_CURRENT_PLAN)

    def test_modify_current_plan_change(self):
        intent = normalize_intent(
            "change the authentication to use JWT instead of session tokens"
        )
        self.assertEqual(intent.route_type, RouteType.MODIFY_CURRENT_PLAN)

    def test_ambiguous_input_empty(self):
        intent = normalize_intent("")
        self.assertIsNotNone(intent.ambiguity)
        self.assertLess(intent.confidence, 0.6)

    def test_ambiguous_input_too_short(self):
        intent = normalize_intent("fix it")
        self.assertIsNotNone(intent.ambiguity)

    def test_keywords_extraction(self):
        intent = normalize_intent("implement user authentication with JWT tokens")
        self.assertIn("user", intent.keywords)
        self.assertIn("authentication", intent.keywords)
        self.assertIn("jwt", intent.keywords)

    def test_complexity_small_for_cache_answer(self):
        intent = normalize_intent("what is the port?")
        self.assertEqual(intent.estimated_complexity, "small")

    def test_complexity_large_for_new_lane(self):
        intent = normalize_intent(
            "implement a complete redesign of the authentication architecture"
        )
        self.assertEqual(intent.estimated_complexity, "large")

    def test_replacement_detection(self):
        intent = normalize_intent("replace the current auth system with OAuth2")
        self.assertTrue(intent.replaces_current_goal)

    def test_supplement_detection(self):
        intent = normalize_intent("also add rate limiting to the API")
        self.assertTrue(intent.supplements_current_goal)

    def test_supplement_chinese(self):
        intent = normalize_intent("顺便把日志也加上")
        self.assertTrue(intent.supplements_current_goal)


if __name__ == "__main__":
    unittest.main()
