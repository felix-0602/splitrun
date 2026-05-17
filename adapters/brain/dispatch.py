"""
Brain DISPATCH — 读 work_units.json，按复杂度决定模型，生成 Lane prompt。

用法：
  dispatcher = BrainDispatcher(project_root)
  lanes = dispatcher.dispatch()  # 返回 Lane 分派计划列表
"""

import json
from pathlib import Path
from datetime import datetime, timezone


class BrainDispatcher:
    """Brain 的分派器：决定哪些 WU 进哪些 Lane，模型路由。"""

    def __init__(self, project_root: Path | str = "."):
        self.root = Path(project_root).resolve()
        self.splitrun = self.root / ".splitrun"

    def dispatch(self) -> list[dict]:
        """读 work_units.json，生成 Lane 分派计划（plan-only，不写 active lane index）。"""
        wus = self._load_pending_wus()
        if not wus:
            return []

        lanes = self._group_into_lanes(wus)
        self._write_lane_plan(lanes)
        return lanes

    def _load_pending_wus(self) -> list[dict]:
        path = self.splitrun / "work_units.json"
        if not path.exists():
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        all_wus = data.get("work_units", [])
        return [w for w in all_wus if w.get("status") == "pending"]

    def _model_for_wu(self, wu: dict) -> str:
        risk = wu.get("risk_level", "medium")
        files_count = len(wu.get("files_allowed", []))
        if risk == "high" or files_count > 3:
            return "pro"
        elif risk == "low" and files_count <= 1:
            return "flash"
        return "pro"

    def _group_into_lanes(self, wus: list[dict]) -> list[dict]:
        """互不依赖的 WU → 不同 Lane（可并行）；有依赖的 → 同一 Lane（串行）。"""
        ready = [w for w in wus if not self._has_pending_deps(w, wus)]
        blocked = [w for w in wus if self._has_pending_deps(w, wus)]

        lanes = []
        # 每个 ready WU 可以独立 Lane（并行）
        for i, wu in enumerate(ready):
            lane_name = f"LANE-{i+1:03d}"
            model = self._model_for_wu(wu)
            lanes.append({
                "lane_id": lane_name,
                "assigned_wus": [wu["id"]],
                "model": model,
                "files_claimed": wu.get("files_allowed", []),
                "status": "planned",
            })

        # 被阻塞的 WU 分组到等待 Lane
        if blocked:
            lanes.append({
                "lane_id": f"LANE-{len(ready)+1:03d}",
                "assigned_wus": [w["id"] for w in blocked],
                "model": "pro",
                "files_claimed": [],
                "status": "blocked",
                "blocked_by": list({d for w in blocked for d in w.get("depends_on", [])}),
            })

        return lanes

    def _has_pending_deps(self, wu: dict, all_wus: list[dict]) -> bool:
        wu_map = {w["id"]: w for w in all_wus}
        for dep_id in wu.get("depends_on", []):
            dep = wu_map.get(dep_id, {})
            if dep.get("status") != "integrated":
                return True
        return False

    def _write_lane_plan(self, lanes: list[dict]) -> None:
        """写 lane 分派计划到 .splitrun/lane_plan.json（plan-only，不含 worktree）。

        与 active lane index（lanes/index.json）分离：
        - lane_plan.json = 分派计划（dispatch 写，人工参考；spawn 当前不消费此文件）
        - lanes/index.json = 活跃 Lane 状态（spawn_lane.register_lane 写）
        """
        plan_path = self.splitrun / "lane_plan.json"
        plan_path.parent.mkdir(parents=True, exist_ok=True)
        plan = []
        for lane in lanes:
            entry = {
                "lane_id": lane["lane_id"],
                "assigned_wus": lane["assigned_wus"],
                "model": lane["model"],
                "files_claimed": lane["files_claimed"],
                "status": lane["status"],
            }
            if lane["status"] == "blocked":
                entry["blocked_by"] = lane.get("blocked_by", [])
            plan.append(entry)
        plan_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def generate_lane_prompt(self, lane: dict, template_path: Path | None = None) -> str:
        """为 Lane 生成 prompt.md 内容。"""
        if template_path and template_path.exists():
            template = template_path.read_text(encoding="utf-8")
        else:
            template = self._default_template()

        wu_ids = ", ".join(lane["assigned_wus"])
        files = ", ".join(lane.get("files_claimed", []))
        model = lane.get("model", "pro")

        return template.format(
            lane_id=lane["lane_id"],
            wu_list=wu_ids,
            files_allowed=files,
            model=model,
        )

    @staticmethod
    def _default_template() -> str:
        return (
            "# Lane: {lane_id}\n\n"
            "## 任务\n"
            "你是 SPLIT-RUN Lane {lane_id}。在隔离的 git worktree 中执行分配的 WU。\n\n"
            "## 分配的 WU\n"
            "{wu_list}\n\n"
            "## 允许修改的文件\n"
            "{files_allowed}\n\n"
            "## 模型\n"
            "{model}\n\n"
            "## 执行流程\n"
            "1. 读 .splitrun/lanes/{lane_id}/.splitrun/work_units.json\n"
            "2. 执行每个 WU，在 files_allowed 边界内工作\n"
            "3. 完成后写 .splitrun/report.json\n\n"
            "## 约束\n"
            "- 只改 files_allowed 内的文件\n"
            "- 不写 root .splitrun/ 元数据\n"
            "- 遇阻→升级给 Brain MONITOR\n"
        )
