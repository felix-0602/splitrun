#!/usr/bin/env python3
"""DEEPSHIP lane 管理器。

lane 是隔离的 git worktree + AI 可读的运行期元数据。
lane 路径本身即为 worktree 根目录：

    .deepship/lanes/<lane-name>/

这让 lane 状态通过 .deepship 统一管理，不在项目旁边散落兄弟目录。
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

DEEPSHIP_DIR = ".deepship"
LANES_DIR = "lanes"
LANES_ARCHIVE_DIR = "lanes-archive"
LANE_BRANCH_PREFIX = "deepship/"
LANE_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")

INITIAL_STATE = {
    "current_state": "READ_CONTEXT",
    "current_milestone": "",
    "current_work_unit": "",
    "last_completed_state": "",
    "next_action": "New lane created. Read handoff.md and Prompt.md before execution.",
    "validation_status": None,
    "repair_count": 0,
    "updated_at": "",
}

INITIAL_WORK_UNITS = {
    "milestone": "",
    "work_units": [],
}

INITIAL_PROMPT = """# Prompt.md - Lane: {lane_name}

## Task Identity
- Lane name: {lane_name}
- Created at: {created_at}

## Goal
1. [Describe the goal before execution]

## Non-goals
- [Describe what this lane must not do]

## Constraints
| Category | Constraint | Reason |
|----------|------------|--------|
| Scope | | |

## Done When
- [ ] [Completion condition]
"""

HANDOFF_TEMPLATE = """# Lane Handoff: {lane_name}

## Goal
Fill in this lane's concrete goal before starting execution.

## Relationship To Main Lane
This lane is isolated from the main worktree and should be merged back through
the lane manager after its work units are integrated.

## Worktree
{worktree_path}

## Branch
{branch}

## Files To Read First
- .deepship/lanes/{lane_name}/lane.json
- .deepship/lanes/{lane_name}/state.json
- .deepship/lanes/{lane_name}/work_units.json
- .deepship/lanes/{lane_name}/Prompt.md

## Operating Rules
- Make code changes only inside the worktree path above.
- Keep lane runtime state in this lane home.
- Do not modify the main worktree while acting as this lane.
- Merge back from the main repository with:
  python adapters/lane/lane.py merge {lane_name}
"""


class LanesRegistry:
    """Read/write .deepship/lanes.json."""

    def __init__(self, depship_dir: str | Path):
        self._path = Path(depship_dir) / "lanes.json"
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def _read(self) -> dict:
        if not self._path.exists():
            return {"lanes": [], "updated_at": ""}
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {"lanes": [], "updated_at": ""}

    def _write(self, data: dict) -> None:
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        tmp.replace(self._path)

    def add(self, entry: dict) -> dict:
        data = self._read()
        names = {lane["name"] for lane in data["lanes"]}
        if entry["name"] in names:
            return {"success": False, "error": f"Lane '{entry['name']}' already exists"}
        entry.setdefault("created_at", datetime.now(timezone.utc).isoformat())
        entry.setdefault("updated_at", entry["created_at"])
        entry.setdefault("status", "active")
        data["lanes"].append(entry)
        self._write(data)
        return {"success": True}

    def remove(self, name: str) -> dict:
        data = self._read()
        before = len(data["lanes"])
        data["lanes"] = [lane for lane in data["lanes"] if lane["name"] != name]
        if len(data["lanes"]) == before:
            return {"success": False, "error": f"Lane '{name}' is not in registry"}
        self._write(data)
        return {"success": True}

    def get(self, name: str) -> dict | None:
        for lane in self._read()["lanes"]:
            if lane["name"] == name:
                return lane
        return None

    def list_all(self) -> list[dict]:
        return self._read()["lanes"]

    def update(self, name: str, **kwargs) -> dict:
        data = self._read()
        for lane in data["lanes"]:
            if lane["name"] == name:
                lane.update(kwargs)
                lane["updated_at"] = datetime.now(timezone.utc).isoformat()
                self._write(data)
                return {"success": True}
        return {"success": False, "error": f"Lane '{name}' is not in registry"}


class LaneManager:
    """Create, list, remove, and merge DEEPSHIP lanes."""

    def __init__(self, project_root: str | Path = "."):
        self.project_root = Path(project_root).resolve()
        self.project_name = self.project_root.name
        self.deepship_root = self.project_root / DEEPSHIP_DIR
        self.lanes_root = self.deepship_root / LANES_DIR
        self.registry = LanesRegistry(self.deepship_root)

    def _lane_home(self, name: str) -> Path:
        return self.lanes_root / name

    def _worktree_path(self, name: str) -> Path:
        return self._lane_home(name)

    def create(self, name: str) -> dict:
        if not LANE_NAME_PATTERN.match(name):
            return {
                "success": False,
                "error": f"Invalid lane name '{name}'. Use lowercase letters, numbers, and hyphens.",
            }

        lane_home = self._lane_home(name)
        lane_path = self._worktree_path(name)
        branch = f"{LANE_BRANCH_PREFIX}{name}"

        if lane_path.exists():
            return {"success": False, "error": f"Lane '{name}' already exists at {lane_path}"}

        self.lanes_root.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            ["git", "-C", str(self.project_root), "worktree", "add", "-b", branch, str(lane_path), "HEAD"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            shutil.rmtree(lane_path, ignore_errors=True)
            stderr = result.stderr.strip()
            if "already exists" in stderr:
                return {"success": False, "error": f"Branch {branch} already exists. Delete it first."}
            return {"success": False, "error": f"git worktree add failed: {stderr}"}

        self._init_lane_files(lane_path, name)

        base_branch = self._get_base_branch()
        base_commit = self._get_base_sha()
        self.registry.add(
            {
                "name": name,
                "branch": branch,
                "worktree_path": str(lane_path),
                "lane_home": str(lane_path / DEEPSHIP_DIR),
                "base_branch": base_branch,
                "base_commit": base_commit,
            }
        )

        return {
            "success": True,
            "name": name,
            "path": str(lane_path),
            "lane_home": str(lane_path / DEEPSHIP_DIR),
            "branch": branch,
        }

    def _init_lane_files(self, lane_path: Path, name: str) -> None:
        ts = datetime.now(timezone.utc).isoformat()
        branch = f"{LANE_BRANCH_PREFIX}{name}"
        lane_home = lane_path / DEEPSHIP_DIR

        lane_meta = {
            "name": name,
            "branch": branch,
            "parent_repo": str(self.project_root),
            "lane_home": str(lane_home),
            "worktree_path": str(lane_path),
            "base_branch": self._get_base_branch(),
            "base_sha": self._get_base_sha(),
            "created_at": ts,
        }
        state = dict(INITIAL_STATE)
        state["current_milestone"] = name
        state["updated_at"] = ts
        work_units = dict(INITIAL_WORK_UNITS)
        work_units["milestone"] = name

        self._write_json(lane_home / "lane.json", lane_meta)
        self._write_json(lane_home / "state.json", state)
        self._write_json(lane_home / "work_units.json", work_units)
        (lane_home / "log.jsonl").write_text(
            json.dumps({"_schema": "deepship-log/1.0", "init": True, "lane": name, "timestamp": ts}, ensure_ascii=False)
            + "\n",
            encoding="utf-8",
        )
        (lane_home / "Prompt.md").write_text(
            INITIAL_PROMPT.format(lane_name=name, created_at=ts),
            encoding="utf-8",
        )
        (lane_home / "handoff.md").write_text(
            HANDOFF_TEMPLATE.format(lane_name=name, worktree_path=lane_path, branch=branch),
            encoding="utf-8",
        )

        (lane_path / "Prompt.md").write_text(
            INITIAL_PROMPT.format(lane_name=name, created_at=ts),
            encoding="utf-8",
        )
        gitignore_path = lane_path / ".gitignore"
        lines = gitignore_path.read_text(encoding="utf-8").splitlines() if gitignore_path.exists() else []
        if DEEPSHIP_DIR not in lines:
            with gitignore_path.open("a", encoding="utf-8") as f:
                f.write(f"\n{DEEPSHIP_DIR}/\n")
        subprocess.run(["git", "-C", str(lane_path), "add", ".gitignore", "Prompt.md"], capture_output=True, text=True, timeout=10)
        subprocess.run(
            ["git", "-C", str(lane_path), "commit", "-m", f"deepship lane init: {name}"],
            capture_output=True,
            text=True,
            timeout=10,
        )

    @staticmethod
    def _write_json(path: Path, data: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def list(self) -> list[dict]:
        registry_lanes = {lane["name"]: lane for lane in self.registry.list_all()}
        lanes: list[dict] = []

        for entry in self.registry.list_all():
            lane_path = Path(entry.get("worktree_path") or self._worktree_path(entry["name"]))
            lane_home = Path(entry.get("lane_home") or lane_path / DEEPSHIP_DIR)
            state = self._read_json(lane_home / "state.json")
            lanes.append(
                {
                    "name": entry["name"],
                    "path": str(lane_path),
                    "lane_home": str(lane_home),
                    "branch": entry.get("branch", ""),
                    "status": entry.get("status", "active"),
                    "state": state.get("current_state", "?"),
                    "milestone": state.get("current_milestone", ""),
                    "wu": state.get("current_work_unit", ""),
                    "base_branch": entry.get("base_branch", ""),
                    "updated_at": state.get("updated_at") or entry.get("updated_at", ""),
                }
            )

        if self.lanes_root.exists():
            for lane_path in sorted(self.lanes_root.iterdir()):
                if not lane_path.is_dir() or lane_path.name in registry_lanes:
                    continue
                lane_home = lane_path / DEEPSHIP_DIR
                state_path = lane_home / "state.json"
                if not state_path.exists():
                    continue
                state = self._read_json(state_path)
                meta = self._read_json(lane_home / "lane.json")
                lanes.append(
                    {
                        "name": lane_path.name,
                        "path": str(lane_path),
                        "lane_home": str(lane_home),
                        "branch": meta.get("branch", ""),
                        "status": "unregistered",
                        "state": state.get("current_state", "?"),
                        "milestone": state.get("current_milestone", ""),
                        "wu": state.get("current_work_unit", ""),
                        "base_branch": meta.get("base_branch", ""),
                        "updated_at": state.get("updated_at", ""),
                    }
                )

        # Legacy discovery: old sibling layout is visible but not the default.
        legacy_root = self.project_root.parent / f"{self.project_name}-lanes"
        if legacy_root.exists():
            for legacy in sorted(legacy_root.iterdir()):
                if legacy.is_dir() and legacy.name not in registry_lanes:
                    lanes.append(
                        {
                            "name": legacy.name,
                            "path": str(legacy),
                            "lane_home": "",
                            "branch": "",
                            "status": "legacy",
                            "state": "?",
                            "milestone": "",
                            "wu": "",
                            "base_branch": "",
                            "updated_at": "",
                        }
                    )
        return lanes

    @staticmethod
    def _read_json(path: Path) -> dict:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def _check_unmerged_work(self, lane_path: Path, branch: str) -> dict:
        result = {"has_uncommitted": False, "has_unmerged_commits": False, "ahead_count": 0}
        try:
            status = subprocess.run(["git", "-C", str(lane_path), "status", "--porcelain"], capture_output=True, text=True, timeout=10)
            if status.stdout.strip():
                result["has_uncommitted"] = True
        except Exception:
            pass

        try:
            base_branch = self._get_base_branch() or "master"
            ahead = subprocess.run(
                ["git", "-C", str(lane_path), "rev-list", "--count", "HEAD", "--not", f"origin/{base_branch}", f"refs/heads/{base_branch}"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            result["ahead_count"] = int(ahead.stdout.strip() or "0")
            result["has_unmerged_commits"] = result["ahead_count"] > 0
        except Exception:
            pass
        return result

    def remove(self, name: str, discard: bool = False) -> dict:
        lane_path = self._worktree_path(name)
        entry = self.registry.get(name) or {}
        lane_path = Path(entry.get("worktree_path") or lane_path)
        lane_home = lane_path / DEEPSHIP_DIR
        branch = entry.get("branch") or f"{LANE_BRANCH_PREFIX}{name}"

        if not lane_path.exists():
            return {"success": False, "error": f"Lane '{name}' does not exist at {lane_path}"}

        work = self._check_unmerged_work(lane_path, branch) if lane_path.exists() else {"has_uncommitted": False, "has_unmerged_commits": False, "ahead_count": 0}
        has_live_work = work["has_uncommitted"] or work["has_unmerged_commits"]
        if has_live_work and not discard:
            details = []
            if work["has_uncommitted"]:
                details.append("uncommitted changes")
            if work["has_unmerged_commits"]:
                details.append(f"{work['ahead_count']} unmerged commits")
            return {"success": False, "error": f"Lane '{name}' has live work ({', '.join(details)}). Use --discard to delete anyway."}

        if lane_path.exists():
            cmd = ["git", "-C", str(self.project_root), "worktree", "remove"]
            if discard:
                cmd.append("--force")
            cmd.append(str(lane_path))
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if result.returncode != 0 and "not a working tree" not in result.stderr:
                return {"success": False, "error": f"git worktree remove failed: {result.stderr.strip()}"}

        subprocess.run(["git", "-C", str(self.project_root), "branch", "-D" if discard else "-d", branch], capture_output=True, text=True, timeout=10)
        shutil.rmtree(lane_path, ignore_errors=True)
        self.registry.remove(name)

        return {
            "success": True,
            "name": name,
            "path": str(lane_path),
            "lane_home": str(lane_home),
            "branch": branch,
            "discarded": has_live_work,
        }

    def _get_base_sha(self) -> str:
        try:
            result = subprocess.run(["git", "-C", str(self.project_root), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5)
            return result.stdout.strip()
        except Exception:
            return ""

    def _get_base_branch(self) -> str:
        try:
            result = subprocess.run(["git", "-C", str(self.project_root), "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, timeout=5)
            return result.stdout.strip()
        except Exception:
            return ""

    def merge(self, name: str, apply: bool = False) -> dict:
        entry = self.registry.get(name) or {}
        lane_path = Path(entry.get("worktree_path") or self._worktree_path(name))
        lane_home = Path(entry.get("lane_home") or lane_path / DEEPSHIP_DIR)
        branch = entry.get("branch") or f"{LANE_BRANCH_PREFIX}{name}"

        if not lane_home.exists() or not lane_path.exists():
            return {"success": False, "error": f"Lane '{name}' does not exist"}

        wu_data = self._read_json(lane_home / "work_units.json")
        not_integrated = [wu["id"] for wu in wu_data.get("work_units", []) if wu.get("status") != "integrated"]
        if not_integrated:
            return {"success": False, "error": f"Work units not integrated: {not_integrated}"}

        dirty = subprocess.run(["git", "-C", str(lane_path), "status", "--porcelain"], capture_output=True, text=True, timeout=10)
        if dirty.stdout.strip():
            return {"success": False, "error": "Lane worktree has uncommitted changes. Commit or discard them first."}

        base_branch = entry.get("base_branch") or self._get_base_branch()
        meta_diff = subprocess.run(
            ["git", "-C", str(lane_path), "diff", "--name-status", f"{base_branch}...HEAD", "--", ".deepship/"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        bad_files = []
        for line in meta_diff.stdout.strip().splitlines():
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) >= 2:
                bad_files.append(f"{parts[0].strip()}\t{parts[1].strip()}")
        if bad_files:
            return {"success": False, "error": "Lane branch contains forbidden .deepship/ changes:\n" + "\n".join(bad_files)}

        diff_result = subprocess.run(
            ["git", "-C", str(self.project_root), "diff", f"{base_branch}...{branch}", "--stat"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        diff_preview = diff_result.stdout.strip()

        if not apply:
            return {
                "success": True,
                "dry_run": True,
                "branch": branch,
                "base_branch": base_branch,
                "diff_preview": diff_preview,
                "message": "DRY RUN - use --apply to merge.",
            }

        current_branch = self._get_base_branch()
        if base_branch and current_branch != base_branch:
            return {"success": False, "error": f"Current branch ({current_branch}) differs from lane base branch ({base_branch})."}

        merge_result = subprocess.run(
            ["git", "-C", str(self.project_root), "merge", "--no-ff", branch, "-m", f"deepship lane merge: {name}"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if merge_result.returncode != 0:
            return {"success": False, "error": f"git merge failed: {merge_result.stderr.strip()[:500]}", "diff_preview": diff_preview}

        self.registry.update(name, status="merged", merged_at=datetime.now(timezone.utc).isoformat())
        return {"success": True, "dry_run": False, "branch": branch, "diff_preview": diff_preview, "message": f"Lane '{name}' merged."}

    def _archive_lane_metadata(self, name: str, lane_home: Path) -> Path:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        archive = self.deepship_root / LANES_ARCHIVE_DIR / f"{name}-{timestamp}"
        archive.mkdir(parents=True, exist_ok=False)
        for item in lane_home.iterdir():
            if item.name == ".git":
                continue
            target = archive / item.name
            if item.is_dir():
                shutil.copytree(item, target)
            else:
                shutil.copy2(item, target)
        manifest = {
            "name": name,
            "archived_at": datetime.now(timezone.utc).isoformat(),
            "source_lane_home": str(lane_home),
        }
        self._write_json(archive / "archive.json", manifest)
        return archive

    def finalize(self, name: str, apply: bool = False) -> dict:
        """Merge a lane back, archive metadata, then remove its worktree."""
        entry = self.registry.get(name) or {}
        lane_path = Path(entry.get("worktree_path") or self._worktree_path(name))
        lane_home = Path(entry.get("lane_home") or lane_path / DEEPSHIP_DIR)

        merge_preview = self.merge(name, apply=False)
        if not merge_preview.get("success"):
            return merge_preview

        if not apply:
            return {
                "success": True,
                "dry_run": True,
                "name": name,
                "path": str(lane_path),
                "lane_home": str(lane_home),
                "branch": merge_preview.get("branch", entry.get("branch", "")),
                "base_branch": merge_preview.get("base_branch", entry.get("base_branch", "")),
                "diff_preview": merge_preview.get("diff_preview", ""),
                "planned_actions": [
                    "merge lane branch into base branch",
                    "archive lane metadata under .deepship/lanes-archive/",
                    "remove lane worktree",
                    "delete lane branch",
                    "remove lane registry entry",
                ],
            }

        merge_result = self.merge(name, apply=True)
        if not merge_result.get("success"):
            return merge_result

        archive = self._archive_lane_metadata(name, lane_home)
        remove_result = self.remove(name, discard=False)
        if not remove_result.get("success"):
            return {
                "success": False,
                "error": f"lane merged and archived, but cleanup failed: {remove_result.get('error')}",
                "archive_path": str(archive),
                "merge_result": merge_result,
            }

        return {
            "success": True,
            "dry_run": False,
            "name": name,
            "path": str(lane_path),
            "lane_home": str(lane_home),
            "archive_path": str(archive),
            "merge_result": merge_result,
            "cleanup_result": remove_result,
            "message": f"Lane '{name}' finalized.",
        }

    def info(self, name: str) -> dict:
        entry = self.registry.get(name) or {}
        lane_path = Path(entry.get("worktree_path") or self._worktree_path(name))
        lane_home = Path(entry.get("lane_home") or lane_path / DEEPSHIP_DIR)
        if not lane_home.exists():
            return {"success": False, "error": f"Lane '{name}' does not exist"}

        state = self._read_json(lane_home / "state.json")
        wus = self._read_json(lane_home / "work_units.json").get("work_units", [])
        wu_counts: dict[str, int] = {}
        for wu in wus:
            status = wu.get("status", "pending")
            wu_counts[status] = wu_counts.get(status, 0) + 1

        return {
            "success": True,
            "name": name,
            "path": str(lane_path),
            "lane_home": str(lane_home),
            "state": state.get("current_state", "?"),
            "milestone": state.get("current_milestone", ""),
            "wu_total": len(wus),
            "wu_counts": wu_counts,
            "updated_at": state.get("updated_at", ""),
        }


def create_lane(name: str, project_root: str | Path = ".") -> dict:
    return LaneManager(project_root).create(name)


def list_lanes(project_root: str | Path = ".") -> list[dict]:
    return LaneManager(project_root).list()


def remove_lane(name: str, project_root: str | Path = ".", discard: bool = False) -> dict:
    return LaneManager(project_root).remove(name, discard=discard)


def main() -> None:
    parser = argparse.ArgumentParser(description="DEEPSHIP lane manager")
    sub = parser.add_subparsers(dest="command", required=True)

    p_create = sub.add_parser("create", help="create a lane")
    p_create.add_argument("name")
    p_create.add_argument("-d", "--project-root", default=".")

    p_list = sub.add_parser("list", help="list lanes")
    p_list.add_argument("-d", "--project-root", default=".")

    p_info = sub.add_parser("info", help="show lane info")
    p_info.add_argument("name")
    p_info.add_argument("-d", "--project-root", default=".")

    p_remove = sub.add_parser("remove", help="remove a lane")
    p_remove.add_argument("name")
    p_remove.add_argument("-d", "--project-root", default=".")
    p_remove.add_argument("--discard", action="store_true")

    p_merge = sub.add_parser("merge", help="merge a lane")
    p_merge.add_argument("name")
    p_merge.add_argument("-d", "--project-root", default=".")
    p_merge.add_argument("--apply", action="store_true")

    p_finalize = sub.add_parser("finalize", help="merge, archive, and remove a lane")
    p_finalize.add_argument("name")
    p_finalize.add_argument("-d", "--project-root", default=".")
    p_finalize.add_argument("--apply", action="store_true")

    args = parser.parse_args()
    mgr = LaneManager(args.project_root)

    if args.command == "create":
        result = mgr.create(args.name)
    elif args.command == "list":
        lanes = mgr.list()
        if not lanes:
            print("(no lanes)")
            return
        for lane in lanes:
            print(f"{lane['name']:20s} {lane['status']:12s} {lane['state']:14s} {lane['path']}")
        return
    elif args.command == "info":
        result = mgr.info(args.name)
    elif args.command == "remove":
        result = mgr.remove(args.name, discard=args.discard)
    elif args.command == "merge":
        result = mgr.merge(args.name, apply=args.apply)
    elif args.command == "finalize":
        result = mgr.finalize(args.name, apply=args.apply)
    else:
        result = {"success": False, "error": "unknown command"}

    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result.get("success"):
        sys.exit(1)


if __name__ == "__main__":
    main()
