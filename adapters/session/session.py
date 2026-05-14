"""DEEPSHIP 会话所有权管理器。"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

DEEPSHIP_DIR = ".deepship"
SESSION_FILE = "session.json"
DEFAULT_STALE_MINUTES = 30


class SessionManager:
    """Read/write .deepship/session.json for a project or lane worktree."""

    def __init__(self, project_root: str | Path = "."):
        self.root = Path(project_root).resolve()
        self._path = self.root / DEEPSHIP_DIR / SESSION_FILE

    def _read(self) -> dict:
        if not self._path.exists():
            return {}
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def _write(self, data: dict) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        tmp.replace(self._path)

    def claim_ownership(self, worktree: str | Path) -> dict:
        worktree_str = str(Path(worktree).resolve())
        old = self._read()
        previous = old.get("owner_worktree", "")
        now = datetime.now(timezone.utc).isoformat()
        data = {
            "owner_worktree": worktree_str,
            "owner_started_at": now,
            "last_heartbeat": now,
        }
        if previous:
            data["previous_owner"] = previous
        self._write(data)
        return {"success": True, "previous_owner": previous or None}

    def is_owner(self, worktree: str | Path) -> bool:
        worktree_str = str(Path(worktree).resolve())
        owner = self._read().get("owner_worktree", "")
        if not owner:
            return True
        return owner == worktree_str

    def is_stale(self, timeout_minutes: int = DEFAULT_STALE_MINUTES) -> bool:
        data = self._read()
        if not data.get("owner_worktree"):
            return True
        try:
            last = datetime.fromisoformat(data["last_heartbeat"])
            elapsed = (datetime.now(timezone.utc) - last).total_seconds()
            return elapsed > timeout_minutes * 60
        except (ValueError, KeyError):
            return True

    def heartbeat(self, worktree: str | Path) -> dict:
        worktree_str = str(Path(worktree).resolve())
        data = self._read()
        owner = data.get("owner_worktree", "")
        if owner and owner != worktree_str:
            return {"success": False, "error": f"not owner; current owner: {owner}"}
        data["last_heartbeat"] = datetime.now(timezone.utc).isoformat()
        self._write(data)
        return {"success": True}

    def release_ownership(self, worktree: str | Path) -> dict:
        worktree_str = str(Path(worktree).resolve())
        data = self._read()
        owner = data.get("owner_worktree", "")
        if owner and owner != worktree_str:
            return {"success": False, "error": f"not owner; current owner: {owner}"}
        data.pop("owner_worktree", None)
        data["released_at"] = datetime.now(timezone.utc).isoformat()
        self._write(data)
        return {"success": True}


def main() -> None:
    parser = argparse.ArgumentParser(description="DEEPSHIP session ownership manager")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--project-root", "-d", default=".")
        p.add_argument("--worktree", default=".")

    add_common(sub.add_parser("claim", help="claim write ownership"))
    add_common(sub.add_parser("heartbeat", help="refresh owner heartbeat"))
    add_common(sub.add_parser("release", help="release write ownership"))
    add_common(sub.add_parser("check", help="check ownership"))

    args = parser.parse_args()
    mgr = SessionManager(args.project_root)
    if args.command == "claim":
        result = mgr.claim_ownership(args.worktree)
    elif args.command == "heartbeat":
        result = mgr.heartbeat(args.worktree)
    elif args.command == "release":
        result = mgr.release_ownership(args.worktree)
    elif args.command == "check":
        result = {"success": mgr.is_owner(args.worktree)}
    else:
        result = {"success": False, "error": "unknown command"}

    print(json.dumps(result, ensure_ascii=False))
    if not result.get("success"):
        sys.exit(1)


if __name__ == "__main__":
    main()
