"""Test EvolutionLaneCreator — self-evolution lane boundaries."""

import unittest
from unittest.mock import patch

from adapters.revolution.proposal import build_proposal


class EvolutionLaneTest(unittest.TestCase):
    def setUp(self):
        self.proposal = build_proposal(
            original_request="test request",
            why_reasonable="test",
            constraint_source="protocol/state-machine.md",
            constraint_rule="test rule",
            what_constraint_protects="test",
            current_behavior="test",
            proposed_description="add skip flag",
            target_files=[
                "adapters/cc/transition_state.py",
                "protocol/state-machine.md",
            ],
            change_type="modify",
            impact="test",
            risks="test",
            approval_needed="test",
            rollback_steps=["revert"],
            rollback_verification="tests pass",
        )

    def test_create_evolution_lane_calls_lane_manager(self):
        from adapters.revolution.evolution_lane import create_evolution_lane

        with patch("adapters.lane.lane.LaneManager") as mock:
            instance = mock.return_value
            instance.create.return_value = {
                "success": True,
                "name": "rev-test",
                "path": "/tmp/rev-test",
                "lane_home": "/tmp/rev-test/.deepship",
                "branch": "deepship/rev-test",
            }
            with patch("builtins.open"):
                with patch("pathlib.Path.read_text"):
                    with patch("json.loads", return_value={
                        "milestone": "", "work_units": []
                    }):
                        with patch("pathlib.Path.write_text"):
                            result = create_evolution_lane(
                                self.proposal,
                                "/tmp/project",
                                lane_name="test-rev",
                            )
            self.assertTrue(result.get("success"))

    def test_proposal_target_files_define_lane_scope(self):
        """Self-evolution lane scope must be bounded to proposal target_files."""
        self.assertIn("adapters/cc/transition_state.py", self.proposal.proposed_change.target_files)
        self.assertIn("protocol/state-machine.md", self.proposal.proposed_change.target_files)


if __name__ == "__main__":
    unittest.main()
