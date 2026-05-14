"""Test RevolutionDetector."""

import unittest

from adapters.revolution.detector import (
    is_deepship_constraint,
    is_reasonable_request,
    should_trigger_revolution,
)


class RevolutionDetectorTest(unittest.TestCase):
    def test_is_deepship_constraint_block(self):
        self.assertTrue(is_deepship_constraint("DEEPSHIP BLOCK: target is outside"))

    def test_is_deepship_constraint_policy(self):
        self.assertTrue(is_deepship_constraint("policy.code_write=false"))

    def test_is_deepship_constraint_files_allowed(self):
        self.assertTrue(is_deepship_constraint(
            "outside current work unit files_allowed"
        ))

    def test_is_deepship_constraint_normal_error(self):
        self.assertFalse(is_deepship_constraint("TypeError: 'NoneType' object"))
        self.assertFalse(is_deepship_constraint("FileNotFoundError"))

    def test_is_reasonable_request_valid(self):
        self.assertTrue(is_reasonable_request("implement a new feature"))

    def test_is_reasonable_request_empty(self):
        self.assertFalse(is_reasonable_request(""))
        self.assertFalse(is_reasonable_request("ab"))

    def test_should_trigger_revolution_true(self):
        ok, reason = should_trigger_revolution(
            user_request="I need to skip VALIDATE for this hotfix",
            block_reason="DEEPSHIP BLOCK: illegal transition EXECUTE -> ADVANCE. Legal: VALIDATE",
            is_normal_bug=False,
            can_work_around=False,
        )
        self.assertTrue(ok, reason)

    def test_should_trigger_revolution_normal_bug(self):
        ok, reason = should_trigger_revolution(
            user_request="fix this test",
            block_reason="TypeError: 'NoneType' has no attribute 'name'",
            is_normal_bug=True,
        )
        self.assertFalse(ok)
        self.assertIn("normal bug", reason)

    def test_should_trigger_revolution_not_deepship_constraint(self):
        ok, reason = should_trigger_revolution(
            user_request="fix this bug",
            block_reason="ImportError: cannot import name 'foo'",
            is_normal_bug=False,
        )
        self.assertFalse(ok)

    def test_should_trigger_revolution_can_work_around(self):
        ok, reason = should_trigger_revolution(
            user_request="write a plan file",
            block_reason="DEEPSHIP BLOCK: outside current work unit",
            is_normal_bug=False,
            can_work_around=True,
        )
        self.assertFalse(ok)

    def test_should_trigger_revolution_trivial_request(self):
        ok, reason = should_trigger_revolution(
            user_request="hi",
            block_reason="DEEPSHIP BLOCK: outside current work unit",
            is_normal_bug=False,
        )
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
