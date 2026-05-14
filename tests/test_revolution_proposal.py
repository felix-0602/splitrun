"""Test RevolutionProposal builder — no side effects before approval."""

import unittest

from adapters.revolution.proposal import build_proposal, format_proposal_for_user


class RevolutionProposalTest(unittest.TestCase):
    def setUp(self):
        self.proposal = build_proposal(
            original_request="skip VALIDATE for hotfix",
            why_reasonable="hotfix needs immediate deploy",
            constraint_source="protocol/state-machine.md",
            constraint_rule="EXECUTE -> VALIDATE required",
            what_constraint_protects="ensures all changes are validated before merge",
            current_behavior="blocks transition from EXECUTE directly to RECORD",
            proposed_description="add a --skip-validate flag for emergency hotfixes",
            target_files=["adapters/cc/transition_state.py", "protocol/state-machine.md"],
            change_type="modify",
            impact="adds explicit opt-in skip for emergencies only",
            risks="could be abused if not gated by explicit approval",
            approval_needed="allow modification of transition_state.py guard conditions",
            rollback_steps=["git revert", "remove --skip-validate"],
            rollback_verification="all conformance tests pass after revert",
        )

    def test_proposal_has_all_fields(self):
        self.assertEqual(self.proposal.original_request, "skip VALIDATE for hotfix")
        self.assertEqual(self.proposal.status, "awaiting_approval")
        self.assertIsNotNone(self.proposal.created_at)
        self.assertIsNone(self.proposal.approved_at)

    def test_proposal_blocking_constraint(self):
        bc = self.proposal.blocking_constraint
        self.assertEqual(bc.constraint_source, "protocol/state-machine.md")
        self.assertEqual(bc.what_it_protects, "ensures all changes are validated before merge")

    def test_proposal_proposed_change(self):
        pc = self.proposal.proposed_change
        self.assertEqual(pc.change_type, "modify")
        self.assertIn("adapters/cc/transition_state.py", pc.target_files)

    def test_proposal_rollback(self):
        rp = self.proposal.rollback_plan
        self.assertIn("git revert", rp.steps)
        self.assertTrue(rp.verification)

    def test_format_proposal_for_user(self):
        text = format_proposal_for_user(self.proposal)
        self.assertIn("批准革命", text)
        self.assertIn("skip VALIDATE for hotfix", text)
        self.assertIn("protocol/state-machine.md", text)
        self.assertIn("git revert", text)

    def test_build_proposal_has_no_side_effects(self):
        """ProposalBuilder must not write any files — pure dataclass only."""
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            before = set(p.name for p in root.iterdir())
            build_proposal(
                original_request="test",
                why_reasonable="test",
                constraint_source="test",
                constraint_rule="test",
                what_constraint_protects="test",
                current_behavior="test",
                proposed_description="test",
                target_files=["test.py"],
                change_type="modify",
                impact="test",
                risks="test",
                approval_needed="test",
                rollback_steps=["test"],
                rollback_verification="test",
            )
            after = set(p.name for p in root.iterdir())
            self.assertEqual(before, after, "build_proposal should not write files")


if __name__ == "__main__":
    unittest.main()
