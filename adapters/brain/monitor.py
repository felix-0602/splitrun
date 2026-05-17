"""
Brain MONITOR — 检查 Lane agent 状态，读 report.json，决定 MERGE 或回 PLAN。

用法：
  monitor = BrainMonitor(project_root)
  decision = monitor.check_all_lanes()  # 返回监控决策
"""

import json
from datetime import datetime, timezone
from pathlib import Path


class BrainMonitor:
    """Brain 的监控器：收 Lane 报告，判定 done/blocked/lost。"""

    def __init__(self, project_root: Path | str = "."):
        self.root = Path(project_root).resolve()
        self.splitrun = self.root / ".splitrun"

    def check_all_lanes(self) -> dict:
        """检查所有 active lane 的状态，返回决策。"""
        index = self._load_lane_index()
        active = {k: v for k, v in index.items() if v.get("status") == "active"}

        reports = {}
        for lane_id, info in active.items():
            report = self._read_lane_report(lane_id, info)
            if report:
                reports[lane_id] = report

        return self._decide(active, reports)

    def _load_lane_index(self) -> dict:
        path = self.splitrun / "lanes" / "index.json"
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _read_lane_report(self, lane_id: str, info: dict) -> dict | None:
        """Read lane report from the lane's worktree. Uses worktree path from index."""
        worktree = info.get("worktree", "")
        if not worktree:
            return None
        path = Path(worktree) / ".splitrun" / "report.json"
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def _decide(self, active: dict, reports: dict) -> dict:
        decision = {
            "action": "wait",
            "reason": "",
            "ready_to_merge": [],
            "blocked_lanes": [],
            "lost_lanes": [],
        }

        for lane_id in active:
            if lane_id in reports:
                r = reports[lane_id]
                status = r.get("status", "blocked")
                if status == "done":
                    decision["ready_to_merge"].append(lane_id)
                elif status == "blocked":
                    decision["blocked_lanes"].append({
                        "lane": lane_id,
                        "reason": r.get("blocked_reason", "unknown"),
                    })
            else:
                # 无报告 — 检查是否超时
                spawned = active[lane_id].get("spawned_at", "")
                if self._is_lost(spawned):
                    decision["lost_lanes"].append(lane_id)

        # 决策
        total = len(active)
        ready = len(decision["ready_to_merge"])
        blocked = len(decision["blocked_lanes"])
        lost = len(decision["lost_lanes"])

        if ready == total and total > 0:
            decision["action"] = "merge"
            decision["reason"] = f"all {total} lane(s) done"
        elif blocked > 0 or lost > 0:
            decision["action"] = "replan"
            decision["reason"] = f"{blocked} blocked, {lost} lost — need replan"
        else:
            decision["action"] = "wait"
            decision["reason"] = f"{ready}/{total} done, waiting for remaining lanes"

        return decision

    @staticmethod
    def _is_lost(spawned_at: str, timeout_minutes: int = 30) -> bool:
        if not spawned_at:
            return False
        try:
            from datetime import timedelta
            spawned = datetime.fromisoformat(spawned_at.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            return (now - spawned) > timedelta(minutes=timeout_minutes)
        except Exception:
            return False
