"""Test A2AHandoff payload build/validate/save/load."""

import tempfile
import unittest
from pathlib import Path

from adapters.interrupt.a2a import A2AHandoff
from adapters.interrupt.schemas import A2AHandoffPayload


class A2AHandoffTest(unittest.TestCase):
    def test_build_creates_valid_payload(self):
        payload = A2AHandoff.build(
            original_input="find login function",
            intent_summary="locate login",
            lane_summary="main lane EXECUTE",
            plan_summary="test milestone",
            constraints=("read-only",),
            expected_output="file path",
            should_not_do=("don't edit",),
        )
        self.assertIsInstance(payload, A2AHandoffPayload)
        valid, reason = A2AHandoff.validate(payload)
        self.assertTrue(valid, reason)

    def test_validate_missing_required_field(self):
        payload = A2AHandoffPayload(
            original_input="",
            normalized_intent_summary="",
            lane_summary="test",
            plan_summary="test",
        )
        valid, reason = A2AHandoff.validate(payload)
        self.assertFalse(valid)
        self.assertIn("original_input", reason)

    def test_save_and_load_roundtrip(self):
        payload = A2AHandoff.build(
            original_input="test request",
            intent_summary="test intent",
            lane_summary="test lane",
            plan_summary="test plan",
            delegated_wu_id="WU-001",
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = A2AHandoff.save(payload, tmp)
            self.assertTrue(path.exists())
            loaded = A2AHandoff.load(path)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.original_input, payload.original_input)
            self.assertEqual(loaded.delegated_wu_id, "WU-001")

    def test_load_nonexistent_file(self):
        result = A2AHandoff.load("/nonexistent/path.json")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
