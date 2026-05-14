"""DEEPSHIP Session Ownership — active session lease management.

.session.json records which worktree owns write permissions.
Hook checks ownership before allowing code_write in EXECUTE/REPAIR.
"""

from adapters.session.arbitration import SessionArbitrator
from adapters.session.session import SessionManager

__all__ = ["SessionManager", "SessionArbitrator"]
