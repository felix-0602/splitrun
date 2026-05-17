"""SPLITRUN v0 shared utilities."""
import os, re, subprocess
from pathlib import Path

SPLITRUN_DIR = ".splitrun"
WORKTREE_PARENT = os.path.join(os.path.expanduser("~"), ".claude", ".splitrun-worktrees")

def find_splitrun_root(start=None):
    current = (start or Path.cwd()).resolve()
    while True:
        if (current / SPLITRUN_DIR).is_dir():
            return current
        parent = current.parent
        if parent == current:
            return None
        current = parent

def _check_wt_available():
    try:
        r = subprocess.run(["git", "worktree", "list"], capture_output=True, text=True, timeout=10)
        return r.returncode == 0
    except Exception:
        return False

def _validate_wu_id(wu_id):
    return bool(re.match(r'^WU-[A-Z0-9][A-Z0-9-]*$', wu_id))

def create_worktree(name, project_root=None):
    """Create a git worktree for a lane from current HEAD.

    Args:
        name: Lane ID (e.g. "LANE-001"), used as worktree dir name and branch suffix.
        project_root: Path to project root. If None, auto-detected via find_splitrun_root().

    Returns:
        Path to the new worktree, or None on failure.
    """
    if not _check_wt_available():
        return None
    root = project_root or find_splitrun_root()
    if not root:
        return None
    wt_path = Path(WORKTREE_PARENT) / name
    wt_path.parent.mkdir(parents=True, exist_ok=True)
    branch = f"lane/{name}"
    try:
        subprocess.run(
            ["git", "-C", str(root), "worktree", "add", str(wt_path), "-b", branch],
            check=True, capture_output=True, text=True, timeout=30
        )
        return wt_path
    except subprocess.CalledProcessError:
        return None
