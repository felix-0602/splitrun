"""DEEPSHIP Parallel Dispatcher v0.1 — 固定 runner + git worktree 隔离.

Usage:
    python adapters/parallel/dispatcher.py --mode auto
    python adapters/parallel/dispatcher.py --mode check
    python adapters/parallel/collector.py
    python adapters/parallel/collector.py --show-diff --cleanup
"""

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
]
