"""Test RevolutionAudit."""

import json
import tempfile
import unittest
from pathlib import Path

from adapters.revolution.audit import log_revolution_event
from adapters.revolution.proposal import build_proposal


class RevolutionAuditTest(unittest.TestCase):
    def setUp(self):
        self.proposal = build_proposal(
            original_request="test request",
            why_reasonable="test reason",
            constraint_source="test/source.md",
            constraint_rule="test rule",
            what_constraint_protects="test protection",
            current_behavior="test behavior",
            proposed_description="test change",
            target_files=["test.py"],
            change_type="modify",
            impact="test impact",
            risks="test risks",
            approval_needed="test approval",
            rollback_steps=["test undo"],
            rollback_verification="test verify",
        )
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / ".deepship").mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def test_log_revolution_event_writes_log(self):
        entry = log_revolution_event("proposed", self.proposal, self.root)
        log_path = self.root / ".deepship" / "log.jsonl"
        self.assertTrue(log_path.exists())
        lines = log_path.read_text(encoding="utf-8").strip().split("\n")
        self.assertEqual(len(lines), 1)
        log_entry = json.loads(lines[0])
        self.assertEqual(log_entry["type"], "revolution")
        self.assertEqual(log_entry["event"], "proposed")
        self.assertEqual(log_entry["original_request"], "test request")

    def test_log_revolution_event_multiple(self):
        log_revolution_event("proposed", self.proposal, self.root)
        log_revolution_event("approved", self.proposal, self.root, "user approved")
        log_path = self.root / ".deepship" / "log.jsonl"
        lines = log_path.read_text(encoding="utf-8").strip().split("\n")
        self.assertEqual(len(lines), 2)

    def test_audit_entry_has_proposal_id(self):
        entry = log_revolution_event("proposed", self.proposal, self.root)
        self.assertTrue(entry.proposal_id)
        self.assertEqual(len(entry.proposal_id), 12)


if __name__ == "__main__":
    unittest.main()
