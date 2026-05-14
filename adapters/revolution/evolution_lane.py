"""EvolutionLaneCreator — 用户批准后创建 self-evolution lane."""

from __future__ import annotations

from pathlib import Path

from adapters.revolution.schemas import RevolutionProposal


def create_evolution_lane(
    proposal: RevolutionProposal,
    project_root: str | Path,
    lane_name: str | None = None,
) -> dict:
    """用户批准 RevolutionProposal 后，创建 self-evolution lane。

    返回 LaneManager.create() 的结果字典，额外包含 proposal 摘要。
    """
    from adapters.lane.lane import LaneManager

    mgr = LaneManager(project_root)
    name = lane_name or f"rev-{_sanitize(proposal.original_request)[:30]}"

    result = mgr.create(name)
    if not result.get("success"):
        return result

    # 将 proposal 摘要写入 lane home
    lane_home = Path(result["lane_home"])
    proposal_summary = {
        "proposal_original_request": proposal.original_request,
        "proposal_reason": proposal.reason_it_is_reasonable,
        "constraint_source": proposal.blocking_constraint.constraint_source,
        "proposed_change": proposal.proposed_change.description,
        "target_files": list(proposal.proposed_change.target_files),
        "created_at": proposal.created_at,
    }
    with open(lane_home / "revolution-proposal.json", "w", encoding="utf-8") as f:
        import json

        json.dump(proposal_summary, f, indent=2, ensure_ascii=False)

    # 设置严格的 WU 边界：只允许修改 target_files
    wu_path = lane_home / "work_units.json"
    import json

    wu_data = json.loads(wu_path.read_text(encoding="utf-8"))
    wu_data["work_units"] = [
        {
            "id": f"{name.upper()}-001",
            "goal": f"Revolution: {proposal.proposed_change.description}",
            "scope": f"Self-evolution: {', '.join(proposal.proposed_change.target_files)}",
            "files_allowed": list(proposal.proposed_change.target_files),
            "depends_on": [],
            "execution_mode": "inline",
            "continuation_mode": "normal",
            "parallel_group": None,
            "risk_level": "high",
            "owner": "orchestrator",
            "status": "pending",
            "acceptance_tests": ["All existing conformance tests pass"],
            "created_at": proposal.created_at,
        }
    ]
    wu_path.write_text(json.dumps(wu_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    return {
        **result,
        "self_evolution": True,
        "proposal_summary": proposal_summary,
    }


def _sanitize(text: str) -> str:
    """将文本转为合法的 lane 名称片段。"""
    import re

    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9-]", "-", text)
    text = re.sub(r"-{2,}", "-", text)
    return text.strip("-")
