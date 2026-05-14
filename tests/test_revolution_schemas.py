"""Test revolution channel data structures."""

import unittest

from adapters.revolution.schemas import (
    RevolutionStatus,
    BlockingConstraint,
    ProposedChange,
    RollbackPlan,
    RevolutionProposal,
    RevolutionAuditEntry,
)


class RevolutionSchemasTest(unittest.TestCase):
    def test_revolution_status_values(self):
        self.assertEqual(RevolutionStatus.DRAFT.value, "draft")
        self.assertEqual(RevolutionStatus.APPROVED.value, "approved")

    def test_blocking_constraint_fields(self):
        bc = BlockingConstraint(
            constraint_source="protocol/state-machine.md",
            constraint_rule="EXECUTE -> VALIDATE required",
            what_it_protects="validation gate",
            current_behavior="blocks skip",
        )
        self.assertEqual(bc.constraint_source, "protocol/state-machine.md")

    def test_proposed_change_all_fields(self):
        pc = ProposedChange(
            description="add skip flag",
            target_files=("file1.py", "file2.md"),
            change_type="add",
            impact="optional skip path",
        )
        self.assertEqual(pc.change_type, "add")
        self.assertEqual(len(pc.target_files), 2)

    def test_rollback_plan(self):
        rp = RollbackPlan(
            steps=("git revert", "run tests"),
            verification="all tests pass",
        )
        self.assertEqual(len(rp.steps), 2)

    def test_revolution_proposal_auto_timestamp(self):
        bc = BlockingConstraint("src", "rule", "protects", "behavior")
        pc = ProposedChange("desc", ("file.py",))
        rp = RollbackPlan(("undo",))
        proposal = RevolutionProposal(
            original_request="test",
            reason_it_is_reasonable="reasonable",
            blocking_constraint=bc,
            proposed_change=pc,
            risks="none",
            approval_needed="approve",
            rollback_plan=rp,
        )
        self.assertTrue(proposal.created_at)
        self.assertEqual(proposal.status, "draft")

    def test_revolution_audit_entry_auto_timestamp(self):
        entry = RevolutionAuditEntry(event="proposed", proposal_id="abc123")
        self.assertTrue(entry.timestamp)
        self.assertEqual(entry.event, "proposed")


if __name__ == "__main__":
    unittest.main()
