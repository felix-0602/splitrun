"""DEEPSHIP 新会话动态仲裁。

不预分配 milestone 给 lane。当新会话进入已有活跃 owner 的项目时介入。
输出仲裁决策：重复请求停止、移交工作给 owner、创建计划修订和 lane 合约、
或要求 owner 停止并重新规划。
"""

from __future__ import annotations

import json
import re
import argparse
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

DEEPSHIP_DIR = ".deepship"
SESSIONS_FILE = "sessions.json"


@dataclass
class ActiveSession:
    id: str
    goal: str
    status: str
    role: str
    plan_revision: str
    worktree_path: str


class SessionArbitrator:
    def __init__(self, project_root: str | Path = "."):
        self.root = Path(project_root).resolve()

    def arbitrate(self, user_request: str, requested_goal: str | None = None) -> dict:
        goal = (requested_goal or user_request).strip()
        owner = self._current_owner()
        if owner is None:
            return {
                "route": "take_ownership",
                "should_create_lane": False,
                "reason": "no active owner session found",
            }

        owner_goal = owner.goal or ""
        if self._same_goal(goal, owner_goal):
            return {
                "route": "duplicate",
                "should_create_lane": False,
                "owner_session_id": owner.id,
                "reason": "request overlaps the active owner goal",
            }

        if self._is_conflict(goal, owner_goal, user_request):
            return {
                "route": "plan_conflict",
                "should_create_lane": False,
                "owner_session_id": owner.id,
                "a2a_handoff": self._handoff(owner, user_request, goal, "stop_and_replan"),
                "reason": "request changes or replaces the active plan",
            }

        if self._belongs_to_owner(goal, owner_goal):
            return {
                "route": "belongs_to_current_owner",
                "should_create_lane": False,
                "owner_session_id": owner.id,
                "a2a_handoff": self._handoff(owner, user_request, goal, "pause_and_reconcile_plan"),
                "reason": "request is in the active owner's responsibility boundary",
            }

        plan_revision = self._plan_revision(user_request, goal, owner)
        return {
            "route": "new_goal_requires_lane",
            "should_create_lane": True,
            "owner_session_id": owner.id,
            "plan_revision": plan_revision,
            "a2a_contract": {
                "type": "new_lane_contract",
                "lane_goal": goal,
                "integration_owner_session_id": owner.id,
                "base_plan": owner.plan_revision or "Plan.md",
                "plan_revision": plan_revision["path"],
                "interfaces_to_define_before_execution": [
                    "shared files and ownership boundaries",
                    "expected integration points",
                    "validation commands for the new goal",
                    "A2A status update format",
                ],
                "must_not": [
                    "start lane execution before plan revision is accepted",
                    "directly overwrite the active owner's plan scope",
                ],
            },
            "a2a_handoff": self._handoff(owner, user_request, goal, "acknowledge_plan_revision"),
            "reason": "request is a distinct goal that needs a coordinated lane",
        }

    def arbitrate_and_persist(self, user_request: str, requested_goal: str | None = None) -> dict:
        decision = self.arbitrate(user_request, requested_goal=requested_goal)
        artifact_id = self._artifact_id(decision)

        if "plan_revision" in decision:
            plan = decision["plan_revision"]
            plan_path = self.root / DEEPSHIP_DIR / "plan-revisions" / Path(plan["path"]).name
            plan_path.parent.mkdir(parents=True, exist_ok=True)
            plan_path.write_text(plan["content"], encoding="utf-8")
            plan["path"] = str(plan_path)

        if "a2a_contract" in decision:
            contract_path = self.root / DEEPSHIP_DIR / "a2a" / f"{artifact_id}.json"
            contract_path.parent.mkdir(parents=True, exist_ok=True)
            contract = dict(decision["a2a_contract"])
            contract["id"] = artifact_id
            contract["created_at"] = datetime.now(timezone.utc).isoformat()
            contract_path.write_text(json.dumps(contract, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            decision["a2a_contract"] = contract
            decision["a2a_contract"]["path"] = str(contract_path)

        if "a2a_handoff" in decision:
            handoff_path = self.root / DEEPSHIP_DIR / "a2a" / f"{artifact_id}-handoff.json"
            handoff_path.parent.mkdir(parents=True, exist_ok=True)
            handoff = dict(decision["a2a_handoff"])
            handoff["id"] = f"{artifact_id}-handoff"
            handoff["created_at"] = datetime.now(timezone.utc).isoformat()
            handoff_path.write_text(json.dumps(handoff, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            decision["a2a_handoff"] = handoff
            decision["a2a_handoff"]["path"] = str(handoff_path)

        prompt_path = self.root / DEEPSHIP_DIR / "prompt-supplements" / f"{artifact_id}.md"
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        prompt_path.write_text(self._prompt_supplement(decision, user_request), encoding="utf-8")
        decision["prompt_supplement"] = {"path": str(prompt_path)}
        return decision

    def _current_owner(self) -> ActiveSession | None:
        data = self._read_json(self.root / DEEPSHIP_DIR / SESSIONS_FILE)
        sessions = data.get("sessions", [])
        for raw in sessions:
            if raw.get("status") in ("executing", "planning", "active") and raw.get("role") == "owner":
                return ActiveSession(
                    id=raw.get("id", ""),
                    goal=raw.get("goal", ""),
                    status=raw.get("status", ""),
                    role=raw.get("role", ""),
                    plan_revision=raw.get("plan_revision", "Plan.md"),
                    worktree_path=raw.get("worktree_path", ""),
                )
        return None

    @staticmethod
    def _read_json(path: Path) -> dict:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    @staticmethod
    def _tokens(text: str) -> set[str]:
        stop = {
            "a",
            "an",
            "the",
            "to",
            "with",
            "and",
            "or",
            "add",
            "implement",
            "continue",
            "handling",
        }
        return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in stop}

    def _same_goal(self, goal: str, owner_goal: str) -> bool:
        g = self._tokens(goal)
        o = self._tokens(owner_goal)
        return bool(g and o and g == o)

    def _belongs_to_owner(self, goal: str, owner_goal: str) -> bool:
        g = self._tokens(goal)
        o = self._tokens(owner_goal)
        if not g or not o:
            return False
        return len(g & o) >= max(1, min(len(o), 2))

    @staticmethod
    def _is_conflict(goal: str, owner_goal: str, request: str) -> bool:
        text = f"{goal} {request}".lower()
        conflict_words = ("replace", "instead", "rewrite", "different protocol", "stop current", "supersede")
        return any(word in text for word in conflict_words) and bool(owner_goal)

    def _plan_revision(self, user_request: str, goal: str, owner: ActiveSession) -> dict:
        base = self.root / (owner.plan_revision or "Plan.md")
        base_content = base.read_text(encoding="utf-8") if base.exists() else ""
        content = (
            base_content.rstrip()
            + "\n\n## Proposed Dynamic Lane Addition\n"
            + f"- New goal: {goal}\n"
            + f"- Source request: {user_request}\n"
            + f"- Integration owner session: {owner.id}\n"
            + "- Before execution: define shared interfaces, file boundaries, validation commands, and A2A status format.\n"
        )
        return {"path": str(self.root / "Plan-2.md"), "content": content}

    @staticmethod
    def _artifact_id(decision: dict) -> str:
        route = decision.get("route", "arbitration")
        goal = decision.get("a2a_contract", {}).get("lane_goal") or decision.get("a2a_handoff", {}).get("goal") or route
        slug = re.sub(r"[^a-z0-9]+", "-", goal.lower()).strip("-") or "request"
        return f"{route}-{slug}"[:96]

    @staticmethod
    def _prompt_supplement(decision: dict, user_request: str) -> str:
        owner = decision.get("owner_session_id", "")
        route = decision.get("route", "")
        goal = decision.get("a2a_contract", {}).get("lane_goal") or decision.get("a2a_handoff", {}).get("goal", "")
        lines = [
            f"# Prompt Supplement: {route}",
            "",
            f"Owner session: {owner}",
            f"Route: {route}",
            f"User request: {user_request}",
            f"Normalized goal: {goal}",
            "",
            "## Required Alignment",
            "- Re-read the current plan and this supplement before continuing.",
            "- Confirm whether the request stays with the owner or requires a lane.",
            "- If a lane is required, accept the A2A contract before execution.",
            "- Do not continue from stale plan assumptions.",
            "",
        ]
        if decision.get("plan_revision"):
            lines.append(f"Plan revision: {decision['plan_revision']['path']}")
        if decision.get("a2a_contract"):
            lines.append(f"A2A contract: {decision['a2a_contract'].get('path', '')}")
        if decision.get("a2a_handoff"):
            lines.append(f"A2A handoff: {decision['a2a_handoff'].get('path', '')}")
        return "\n".join(lines) + "\n"

    @staticmethod
    def _handoff(owner: ActiveSession, user_request: str, goal: str, action: str) -> dict:
        return {
            "to_session_id": owner.id,
            "requested_action": action,
            "goal": goal,
            "message": (
                f"New request received: {user_request}. "
                f"Normalized goal: {goal}. "
                f"Please {action.replace('_', ' ')} before continuing."
            ),
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="DEEPSHIP new-session arbitration")
    parser.add_argument("--project-root", "-d", default=".")
    parser.add_argument("--request", required=True, help="raw user request")
    parser.add_argument("--goal", default="", help="normalized requested goal")
    parser.add_argument("--persist", action="store_true", help="write plan revision, A2A, and prompt supplement artifacts")
    args = parser.parse_args()

    arbitrator = SessionArbitrator(args.project_root)
    if args.persist:
        result = arbitrator.arbitrate_and_persist(args.request, requested_goal=args.goal or None)
    else:
        result = arbitrator.arbitrate(args.request, requested_goal=args.goal or None)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result.get("route") == "plan_conflict":
        sys.exit(2)


if __name__ == "__main__":
    main()
