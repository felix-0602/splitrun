"""DEEPSHIP Revolution Channel.

革命通道：当合理请求被 DEEPSHIP 自身框架约束拦住时，
通过显式用户审批实现受控的框架自进化。
"""

from adapters.revolution.schemas import (
    RevolutionStatus,
    BlockingConstraint,
    ProposedChange,
    RevolutionProposal,
    RevolutionAuditEntry,
    RollbackPlan,
)
from adapters.revolution.detector import (
    is_deepship_constraint,
    is_reasonable_request,
    should_trigger_revolution,
)
from adapters.revolution.proposal import build_proposal, format_proposal_for_user
from adapters.revolution.evolution_lane import create_evolution_lane
from adapters.revolution.audit import log_revolution_event

__all__ = [
    "RevolutionStatus",
    "BlockingConstraint",
    "ProposedChange",
    "RevolutionProposal",
    "RevolutionAuditEntry",
    "RollbackPlan",
    "is_deepship_constraint",
    "is_reasonable_request",
    "should_trigger_revolution",
    "build_proposal",
    "format_proposal_for_user",
    "create_evolution_lane",
    "log_revolution_event",
]
