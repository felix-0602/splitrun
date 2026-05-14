"""Integration test: detect -> propose -> audit pipeline."""

import tempfile
import unittest
from pathlib import Path

from adapters.revolution.detector import should_trigger_revolution
from adapters.revolution.proposal import build_proposal, format_proposal_for_user
from adapters.revolution.audit import log_revolution_event


class RevolutionIntegrationTest(unittest.TestCase):
    def test_detect_then_propose_pipeline(self):
        """Detect a revolution-worthy scenario, build proposal, format for user."""
        ok, _ = should_trigger_revolution(
            user_request="I need to skip VALIDATE for this emergency hotfix",
            block_reason="DEEPSHIP BLOCK: illegal transition EXECUTE -> RECORD",
            is_normal_bug=False,
            can_work_around=False,
        )
        self.assertTrue(ok)

        proposal = build_proposal(
            original_request="skip VALIDATE for emergency hotfix",
            why_reasonable="emergency hotfix cannot wait for full validation cycle",
            constraint_source="protocol/state-machine.md",
            constraint_rule="EXECUTE -> VALIDATE is the only legal transition",
            what_constraint_protects="ensures all code changes pass validation",
            current_behavior="blocks direct advance to RECORD",
            proposed_description="add --emergency flag to allow skip for hotfixes",
            target_files=["adapters/cc/transition_state.py"],
            change_type="modify",
            impact="controlled bypass for emergencies",
            risks="abuse potential if not gated by explicit approval",
            approval_needed="allow emergency skip in transition_state.py",
            rollback_steps=["git revert", "re-run all conformance tests"],
            rollback_verification="all tests pass after revert",
        )

        text = format_proposal_for_user(proposal)
        self.assertIn("批准革命", text)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".deepship").mkdir()
            entry = log_revolution_event("proposed", proposal, root)
            self.assertTrue(entry.proposal_id)

    def test_normal_bug_does_not_trigger(self):
        """A normal test failure should not trigger revolution."""
        ok, reason = should_trigger_revolution(
            user_request="fix this failing test",
            block_reason="AssertionError: expected True",
            is_normal_bug=True,
        )
        self.assertFalse(ok)
        self.assertIn("normal bug", reason.lower())

    def test_ambiguous_request_does_not_trigger(self):
        """Unclear request should not trigger revolution."""
        ok, _ = should_trigger_revolution(
            user_request="",
            block_reason="DEEPSHIP BLOCK: write target outside project",
        )
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
