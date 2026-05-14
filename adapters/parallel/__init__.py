"""DEEPSHIP Adapters — dispatcher, collector, rotate, interrupt routing, revolution channel."""

from adapters.parallel.dispatcher import (
    dispatch,
    find_parallel_wus,
    group_by_fork,
    load_work_units,
    create_worktree,
    cleanup_worktrees,
)
from adapters.parallel.collector import (
    collect,
    collect_results,
    validate_boundary,
    validate_tests,
    validate_format,
    check_conflicts,
)
from adapters.parallel.rotate import (
    rotate,
    write_continuation,
)
from adapters.parallel.spawn_lane import (
    LaneSpawner,
    list_active_lanes,
    spawn_interactive_terminal,
)
from adapters.interrupt.schemas import (
    RouteType,
    ReconciliationOutcome,
    InterruptContext,
    NormalizedIntent,
    A2AHandoffPayload,
    RouteDecision,
    ReconciliationResult,
)
from adapters.revolution.schemas import (
    RevolutionProposal,
    BlockingConstraint,
    RevolutionAuditEntry,
)

__all__ = [
    "dispatch",
    "find_parallel_wus",
    "group_by_fork",
    "load_work_units",
    "create_worktree",
    "cleanup_worktrees",
    "collect",
    "collect_results",
    "validate_boundary",
    "validate_tests",
    "validate_format",
    "check_conflicts",
    "rotate",
    "write_continuation",
    "RouteType",
    "ReconciliationOutcome",
    "InterruptContext",
    "NormalizedIntent",
    "A2AHandoffPayload",
    "RouteDecision",
    "ReconciliationResult",
    "RevolutionProposal",
    "BlockingConstraint",
    "RevolutionAuditEntry",
    "LaneSpawner",
    "list_active_lanes",
    "spawn_interactive_terminal",
]
