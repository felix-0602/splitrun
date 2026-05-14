"""RevolutionAudit — 革命审计日志."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from adapters.revolution.schemas import RevolutionAuditEntry, RevolutionProposal


def log_revolution_event(
    event: str,
    proposal: RevolutionProposal,
    project_root: str | Path,
    detail: str = "",
) -> RevolutionAuditEntry:
    """将革命事件追加到 .deepship/log.jsonl 审计轨迹。

    返回生成的 RevolutionAuditEntry。
    """
    root = Path(project_root)
    deepship_dir = root / ".deepship"
    deepship_dir.mkdir(parents=True, exist_ok=True)

    entry = RevolutionAuditEntry(
        event=event,
        proposal_id=_proposal_id(proposal),
        detail=detail,
    )

    log_path = deepship_dir / "log.jsonl"
    log_entry = {
        "type": "revolution",
        "event": entry.event,
        "proposal_id": entry.proposal_id,
        "original_request": proposal.original_request,
        "constraint_source": proposal.blocking_constraint.constraint_source,
        "approved": proposal.approved_at is not None,
        "detail": detail,
        "timestamp": entry.timestamp,
    }
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    return entry


def _proposal_id(proposal: RevolutionProposal) -> str:
    """从提案生成稳定的短 ID。"""
    import hashlib

    key = f"{proposal.original_request}|{proposal.blocking_constraint.constraint_source}|{proposal.created_at}"
    return hashlib.sha256(key.encode()).hexdigest()[:12]
