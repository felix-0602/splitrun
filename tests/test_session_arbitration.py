import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from adapters.session.arbitration import SessionArbitrator


def _project() -> Path:
    root = Path(tempfile.mkdtemp())
    (root / ".deepship").mkdir()
    (root / "Plan.md").write_text(
        "# Plan\n\n## Current Goal\nImplement session ownership.\n\n## Interfaces\n- session.json owns writes\n",
        encoding="utf-8",
    )
    (root / ".deepship" / "sessions.json").write_text(
        json.dumps(
            {
                "sessions": [
                    {
                        "id": "s-main",
                        "role": "owner",
                        "status": "executing",
                        "goal": "Implement session ownership",
                        "plan_revision": "Plan.md",
                        "worktree_path": str(root),
                    }
                ]
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return root


class TestSessionArbitration:
    def test_duplicate_request_stops_new_session(self):
        root = _project()
        result = SessionArbitrator(root).arbitrate(
            "Continue implementing session ownership",
            requested_goal="Implement session ownership",
        )

        assert result["route"] == "duplicate"
        assert result["should_create_lane"] is False
        assert result["owner_session_id"] == "s-main"

    def test_owner_scope_request_generates_a2a_handoff(self):
        root = _project()
        result = SessionArbitrator(root).arbitrate(
            "Add heartbeat timeout handling to session ownership",
            requested_goal="Implement session ownership heartbeat timeout",
        )

        assert result["route"] == "belongs_to_current_owner"
        handoff = result["a2a_handoff"]
        assert handoff["to_session_id"] == "s-main"
        assert "heartbeat timeout" in handoff["message"]
        assert handoff["requested_action"] == "pause_and_reconcile_plan"

    def test_new_goal_requires_plan_revision_and_lane_contract(self):
        root = _project()
        result = SessionArbitrator(root).arbitrate(
            "Add interrupt routing with A2A contracts",
            requested_goal="Interrupt routing",
        )

        assert result["route"] == "new_goal_requires_lane"
        assert result["should_create_lane"] is True
        assert result["plan_revision"]["path"].endswith("Plan-2.md")
        assert "Interrupt routing" in result["plan_revision"]["content"]
        assert result["a2a_contract"]["lane_goal"] == "Interrupt routing"
        assert result["a2a_contract"]["integration_owner_session_id"] == "s-main"

    def test_plan_conflict_requires_owner_to_replan(self):
        root = _project()
        result = SessionArbitrator(root).arbitrate(
            "Replace the session ownership model with a different protocol",
            requested_goal="Replace session ownership",
        )

        assert result["route"] == "plan_conflict"
        assert result["should_create_lane"] is False
        assert result["a2a_handoff"]["requested_action"] == "stop_and_replan"

    def test_cli_outputs_arbitration_json(self):
        root = _project()
        script = Path(__file__).resolve().parents[1] / "adapters" / "session" / "arbitration.py"
        result = subprocess.run(
            [
                sys.executable,
                str(script),
                "--project-root",
                str(root),
                "--request",
                "Add interrupt routing with A2A contracts",
                "--goal",
                "Interrupt routing",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)
        assert data["route"] == "new_goal_requires_lane"

    def test_persist_writes_plan_revision_a2a_and_prompt_supplement(self):
        root = _project()
        result = SessionArbitrator(root).arbitrate_and_persist(
            "Add interrupt routing with A2A contracts",
            requested_goal="Interrupt routing",
        )

        assert result["route"] == "new_goal_requires_lane"
        plan_path = Path(result["plan_revision"]["path"])
        a2a_path = Path(result["a2a_contract"]["path"])
        prompt_path = Path(result["prompt_supplement"]["path"])

        assert plan_path.exists()
        assert a2a_path.exists()
        assert prompt_path.exists()
        assert ".deepship" in str(plan_path)
        assert "Interrupt routing" in plan_path.read_text(encoding="utf-8")

        a2a = json.loads(a2a_path.read_text(encoding="utf-8"))
        assert a2a["type"] == "new_lane_contract"
        assert a2a["lane_goal"] == "Interrupt routing"

        prompt = prompt_path.read_text(encoding="utf-8")
        assert "s-main" in prompt
        assert "Interrupt routing" in prompt
