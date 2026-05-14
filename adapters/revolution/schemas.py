"""DEEPSHIP Revolution Channel — 数据结构."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum


class RevolutionStatus(Enum):
    DRAFT = "draft"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    IMPLEMENTING = "implementing"
    COMPLETED = "completed"
    ROLLED_BACK = "rolled_back"


@dataclass(frozen=True)
class BlockingConstraint:
    constraint_source: str
    constraint_rule: str
    what_it_protects: str
    current_behavior: str


@dataclass(frozen=True)
class ProposedChange:
    description: str
    target_files: tuple[str, ...]
    change_type: str = "modify"
    impact: str = ""


@dataclass(frozen=True)
class RollbackPlan:
    steps: tuple[str, ...]
    verification: str = ""


@dataclass(frozen=True)
class RevolutionProposal:
    original_request: str
    reason_it_is_reasonable: str
    blocking_constraint: BlockingConstraint
    proposed_change: ProposedChange
    risks: str
    approval_needed: str
    rollback_plan: RollbackPlan
    status: str = "draft"
    created_at: str = ""
    approved_at: str | None = None
    evolution_lane: str | None = None

    def __post_init__(self):
        if not self.created_at:
            object.__setattr__(self, "created_at", datetime.now(timezone.utc).isoformat())


@dataclass(frozen=True)
class RevolutionAuditEntry:
    event: str
    proposal_id: str
    detail: str = ""
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            object.__setattr__(self, "timestamp", datetime.now(timezone.utc).isoformat())
