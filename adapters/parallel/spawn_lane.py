#!/usr/bin/env python3
"""
SPLITRUN Lane Spawner v0.1 — 即时 lane 创建，集成 worktree + 交互式终端.

lane = git worktree + 独立 Claude Code 会话 + lane_id.json 自动身份发现.
与 dispatcher 互补: dispatcher 批量分派预定义 WU (claude -p 非交互),
spawn_lane 即时创建交互式 lane ("想到就开").

权限: 新 CC 会话默认 dontAsk (不允许写). spawn_lane 通过
--permission-mode acceptEdits 解决, lane 在隔离 worktree 中运行.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Support direct CLI invocation: python adapters/parallel/spawn_lane.py --list
if __name__ == "__main__" and __package__ is None:
    _PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
    sys.path.insert(0, str(_PROJECT_ROOT))

from adapters.parallel._utils import (
        SPLITRUN_DIR,
        WORKTREE_PARENT,
        _check_wt_available,
        create_worktree,
        find_splitrun_root,
    )

LANES_DIR = "lanes"
LANE_ID_PATTERN = r"^LANE-\d{3}$"
ALLOWED_TOOLS = "Read,Write,Edit,Bash,Glob,Grep,Task,Skill,Agent"
ACTIVE_LANE_STATUSES = {"active", "pending", "executing", "in_progress"}


def _normalize_claim_path(path: str, project_root: Path) -> str:
    raw = str(path).replace("\\", "/").strip()
    if not raw:
        return ""
    try:
        p = Path(path)
        if p.is_absolute():
            return p.resolve().relative_to(project_root.resolve()).as_posix()
    except (OSError, ValueError):
        pass
    return raw.lstrip("./")


def _claim_matches(pattern: str, target: str) -> bool:
    pattern = pattern.replace("\\", "/").rstrip("/")
    target = target.replace("\\", "/").rstrip("/")
    if not pattern or not target:
        return False
    if any(ch in pattern for ch in "*?[]"):
        return fnmatch.fnmatch(target, pattern)
    return target == pattern or target.startswith(pattern + "/")


def _load_lane_index(project_root: Path) -> dict[str, Any]:
    index_path = project_root / SPLITRUN_DIR / LANES_DIR / "index.json"
    if not index_path.exists():
        return {}
    try:
        data = json.loads(index_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def find_file_claim_conflicts(
    project_root: Path,
    files_claimed: list[str] | None,
    current_lane_id: str | None = None,
) -> list[dict[str, str]]:
    requested = [
        _normalize_claim_path(path, project_root)
        for path in (files_claimed or [])
        if str(path).strip()
    ]
    if not requested:
        return []

    conflicts = []
    for lane_id, info in _load_lane_index(project_root).items():
        if lane_id == current_lane_id:
            continue
        if info.get("status") not in ACTIVE_LANE_STATUSES:
            continue
        existing = [
            _normalize_claim_path(path, project_root)
            for path in info.get("files_claimed", [])
            if str(path).strip()
        ]
        for requested_path in requested:
            for existing_path in existing:
                if _claim_matches(existing_path, requested_path) or _claim_matches(
                    requested_path, existing_path
                ):
                    conflicts.append(
                        {
                            "lane_id": lane_id,
                            "requested": requested_path,
                            "claimed": existing_path,
                        }
                    )
    return conflicts


def assert_no_file_claim_conflicts(
    project_root: Path, files_claimed: list[str] | None, current_lane_id: str | None = None
) -> None:
    conflicts = find_file_claim_conflicts(project_root, files_claimed, current_lane_id)
    if conflicts:
        first = conflicts[0]
        raise ValueError(
            "File claim conflict: "
            f"{first['requested']} is already claimed by {first['lane_id']} "
            f"({first['claimed']})"
        )


def _next_lane_id(project_root: Path) -> str:
    lanes_dir = project_root / SPLITRUN_DIR / LANES_DIR
    if not lanes_dir.exists():
        return "LANE-001"
    existing = []
    for f in lanes_dir.iterdir():
        if f.suffix in (".json", ".md") and f.stem.startswith("LANE-"):
            existing.append(f.stem)
    if not existing:
        return "LANE-001"
    nums = []
    for e in existing:
        try:
            nums.append(int(e.split("-")[1]))
        except (IndexError, ValueError):
            pass
    return f"LANE-{max(nums) + 1:03d}" if nums else "LANE-001"


def write_lane_identity(worktree_path: Path, lane_id: str, task_summary: str) -> Path:
    """在 worktree 写入 .splitrun/lane_id.json. 新会话 READ_CONTEXT 自动发现."""
    lane_splitrun = worktree_path / SPLITRUN_DIR
    lane_splitrun.mkdir(parents=True, exist_ok=True)
    identity = {
        "lane_id": lane_id,
        "spawned_at": datetime.now(timezone.utc).isoformat(),
        "task_summary": task_summary,
        "status": "active",
    }
    identity_path = lane_splitrun / "lane_id.json"
    identity_path.write_text(
        json.dumps(identity, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return identity_path


def write_lane_task(worktree_path: Path, lane_id: str, task: str) -> Path:
    """在 worktree 写入完整任务文件."""
    task_dir = worktree_path / SPLITRUN_DIR / LANES_DIR
    task_dir.mkdir(parents=True, exist_ok=True)
    task_content = f"""# {lane_id}: Lane Task

{task}

---
spawned_at: {datetime.now(timezone.utc).isoformat()}
lane_id: {lane_id}
worktree: {worktree_path}

## 开始
Lane ID: {lane_id}. 执行 READ_CONTEXT:
1. 读取 .splitrun/lane_id.json 确认身份
2. 读取本文件了解任务
3. 在 files_claimed 边界内完成工作
4. 完成后写 .splitrun/report.json 格式:
   {"lane_id": "{lane_id}", "status": "done|blocked",
    "changed_files": [...], "test_results": "...",
    "result": "一句话总结"}
"""
    task_path = task_dir / f"{lane_id}.md"
    task_path.write_text(task_content, encoding="utf-8")
    return task_path


def register_lane(
    project_root: Path,
    lane_id: str,
    task_summary: str,
    worktree_path: Path,
    files_claimed: list[str] | None = None,
) -> None:
    """在主仓库 lanes/index.json 注册 lane."""
    lanes_dir = project_root / SPLITRUN_DIR / LANES_DIR
    lanes_dir.mkdir(parents=True, exist_ok=True)
    index_path = lanes_dir / "index.json"
    index = {}
    if index_path.exists():
        try:
            index = json.loads(index_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    index[lane_id] = {
        "status": "active",
        "task": task_summary,
        "worktree": str(worktree_path),
        "files_claimed": [
            _normalize_claim_path(path, project_root)
            for path in (files_claimed or [])
            if str(path).strip()
        ],
        "spawned_at": datetime.now(timezone.utc).isoformat(),
        "spawned_by": "spawn_lane.py",
    }
    index_path.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")


def _resolve_claude_permission_mode() -> str:
    """CC 默认 dontAsk → acceptEdits 解决 lane 写权限问题."""
    return os.environ.get("SPLITRUN_LANE_PERMISSION_MODE", "acceptEdits")


def spawn_interactive_terminal(
    lane_id: str,
    worktree_path: Path,
    initial_prompt: str,
) -> subprocess.Popen | None:
    """在 Windows Terminal 启动交互式 CC 会话 (非 -p 模式)."""
    if not _check_wt_available():
        print("[ERROR] 需要 Windows Terminal (wt.exe).")
        return None

    permission_mode = _resolve_claude_permission_mode()
    cc_cmd = (
        f'cd "{worktree_path}" && claude '
        f"--permission-mode {permission_mode} "
        f'--allowedTools "{ALLOWED_TOOLS}" '
        f'"{initial_prompt}"'
    )

    cmd = ["wt.exe", "--title", lane_id, "bash", "-c", cc_cmd]

    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        print(f"  [SPAWNED] {lane_id}  worktree={worktree_path}")
        print(f"  [PERM]    mode={permission_mode}")
        return proc
    except FileNotFoundError:
        print(f"  [FAILED] {lane_id} -- wt.exe not found.")
        return None


class LaneSpawner:
    """Lane 创建器 -- 可编程接口."""

    def __init__(self, project_root: Path | None = None):
        self.root = project_root or find_splitrun_root()
        if self.root is None:
            raise FileNotFoundError("No .splitrun/ directory found.")

    def spawn(
        self,
        task: str,
        files: list[str] | None = None,
        lane_id: str | None = None,
    ) -> dict[str, Any]:
        if lane_id is None:
            lane_id = _next_lane_id(self.root)
        elif not re.match(LANE_ID_PATTERN, lane_id):
            raise ValueError(
                f"Invalid lane ID: {lane_id} (expected {LANE_ID_PATTERN})"
            )

        assert_no_file_claim_conflicts(self.root, files, lane_id)

        print(f"[LANE] {lane_id} creating...")

        wt_path = create_worktree(lane_id, project_root=self.root)
        if wt_path is None:
            raise RuntimeError(f"Worktree creation failed: {lane_id}")

        full_task = task
        if files:
            full_task += "\n\n## Suggested files\n" + "\n".join(
                f"- `{f}`" for f in files
            )
            full_task += (
                "\n\n(These are suggestions -- verify during MAP_REALITY.)"
            )

        write_lane_identity(wt_path, lane_id, task[:100])
        task_path = write_lane_task(wt_path, lane_id, full_task)
        register_lane(self.root, lane_id, task[:100], wt_path, files)

        initial_prompt = (
            f"SPLITRUN lane {lane_id} activated. "
            f"Run READ_CONTEXT: read .splitrun/lane_id.json, "
            f"then .splitrun/lanes/{lane_id}.md. "
            f"Proceed through SPLITRUN state machine independently."
        )

        proc = spawn_interactive_terminal(lane_id, wt_path, initial_prompt)

        result = {
            "lane_id": lane_id,
            "worktree_path": wt_path,
            "task_path": task_path,
            "proc": proc,
        }

        if proc:
            print(f"[LANE] {lane_id} launched -- switch to new terminal tab.")
        else:
            print(f"[LANE] {lane_id} created, manual start:")
            print(f"       cd {wt_path} && claude")

        return result


def list_active_lanes(project_root: Path | None = None) -> list[dict]:
    root = project_root or find_splitrun_root()
    if root is None:
        print("[ERROR] No .splitrun/ directory.")
        return []

    index_path = root / SPLITRUN_DIR / LANES_DIR / "index.json"
    if not index_path.exists():
        print("(no active lanes)")
        return []

    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        print("(lane index corrupted)")
        return []

    active = [
        {"lane_id": lid, **info}
        for lid, info in index.items()
        if info.get("status") == "active"
    ]

    if not active:
        print("(no active lanes)")
        return []

    print(f"Active lanes ({len(active)}):")
    for lane in active:
        print(f"  {lane['lane_id']}  {lane.get('task', '?')[:60]}")
        print(f"           worktree: {lane.get('worktree', '?')}")
        print(f"           spawned:  {lane.get('spawned_at', '?')}")
    return active


def main() -> None:
    parser = argparse.ArgumentParser(
        description="SPLITRUN Lane Spawner -- instant lane (worktree + interactive terminal)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  python adapters/parallel/spawn_lane.py "fix profiles hook"
  python adapters/parallel/spawn_lane.py "refactor state machine" -f protocol/state-machine.md
  python adapters/parallel/spawn_lane.py --task-file .splitrun/lanes/my-task.md
  python adapters/parallel/spawn_lane.py --list
        """,
    )
    parser.add_argument("task", nargs="?", help="Task description")
    parser.add_argument("--task-file", type=str, help="Read task from file")
    parser.add_argument(
        "--files", "-f", type=str, help="Suggested files, comma-separated"
    )
    parser.add_argument(
        "--lane-id", type=str, help="Lane ID (auto-assigned if omitted)"
    )
    parser.add_argument(
        "--project-root", "-d", type=str, help="Project root directory"
    )
    parser.add_argument(
        "--list", "-l", action="store_true", help="List active lanes"
    )

    args = parser.parse_args()
    root = Path(args.project_root) if args.project_root else None

    if args.list:
        list_active_lanes(root)
        return

    if args.task_file:
        task_path = Path(args.task_file)
        if not task_path.exists():
            print(f"[ERROR] Task file not found: {task_path}")
            sys.exit(1)
        task = task_path.read_text(encoding="utf-8")
    elif args.task:
        task = args.task
    else:
        print("[ERROR] Need task description or --task-file.")
        sys.exit(1)

    files = args.files.split(",") if args.files else None

    try:
        spawner = LaneSpawner(root)
        result = spawner.spawn(task=task, files=files, lane_id=args.lane_id)
        if result["proc"] is None:
            sys.exit(1)
    except (FileNotFoundError, RuntimeError, ValueError) as e:
        print(f"[ERROR] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
