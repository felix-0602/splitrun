"""
SPLIT-RUN hard gates — 从 skill 文档提取的可测试判定逻辑。

这些函数实现 splitrun-land/status 的门禁契约，
使执行质量不再依赖模型读文档。
"""

import json
import re
from pathlib import Path
from typing import Callable, Optional


# ── Lane index schema (verify.py contract) ──────────────────────────

LANE_INDEX_REQUIRED_FIELDS = ["status", "task", "worktree", "files_claimed", "spawned_at"]


def validate_lane_index_entry(entry: dict) -> list[str]:
    """返回缺失的必填字段列表。空列表 = 通过。"""
    return [k for k in LANE_INDEX_REQUIRED_FIELDS if k not in entry]


# ── Scope recommendation parsing ───────────────────────────────────

RECOMMENDATION_PATTERN = re.compile(r"^recommendation:\s*(spawn|do_not_spawn)\s*$", re.MULTILINE)

VALID_RECOMMENDATIONS = {"spawn", "do_not_spawn"}


def parse_recommendation(scope_text: str) -> Optional[str]:
    """从 scope.md 文本中提取 recommendation 值。

    返回 'spawn'、'do_not_spawn' 或 None（未找到/格式错误）。
    """
    m = RECOMMENDATION_PATTERN.search(scope_text)
    if not m:
        return None
    return m.group(1)


# ── File claim matching (shared by spawn_lane + boundary gate) ────

def claim_matches(pattern: str, target: str) -> bool:
    """检查 target 文件路径是否匹配 claimed pattern。

    支持精确匹配、前缀匹配（目录）、glob 通配符。
    """
    import fnmatch

    pattern = pattern.replace("\\", "/").rstrip("/")
    target = target.replace("\\", "/").rstrip("/")
    if not pattern or not target:
        return False
    if any(ch in pattern for ch in "*?[]"):
        return fnmatch.fnmatch(target, pattern)
    return target == pattern or target.startswith(pattern + "/")


# ── Boundary gate (splitrun-land Step 2) ──────────────────────────

def check_boundary(changed_files: list[str], files_claimed: list[str]) -> dict:
    """检查 changed_files 是否全部在 files_claimed 边界内。

    Returns:
        {"pass": bool, "out_of_bounds": list[str], "in_bounds": list[str]}
    """
    out_of_bounds = []
    in_bounds = []
    for f in changed_files:
        if any(claim_matches(claim, f) for claim in files_claimed):
            in_bounds.append(f)
        else:
            out_of_bounds.append(f)
    return {
        "pass": len(out_of_bounds) == 0,
        "out_of_bounds": out_of_bounds,
        "in_bounds": in_bounds,
    }


# ── Land determination gate (splitrun-status Step 4) ───────────────

LAND_OK = "CAN LAND"
LAND_WAITING = "CANNOT LAND — waiting"
LAND_BLOCKED = "CANNOT LAND — blocked"
LAND_BOUNDARY = "CANNOT LAND — boundary"
LAND_NOTHING = "NOTHING TO LAND"


def determine_land_status(lanes: list[dict]) -> str:
    """根据 Lane 状态列表判定是否可以 land。

    每条 lane dict 需包含:
        status: 'done' | 'active' | 'blocked' | ...
        has_report: bool
        has_test_results: bool
        boundary_pass: True | False | None (None = 未检查)
    """
    if not lanes:
        return LAND_NOTHING

    active_lanes = [l for l in lanes if l.get("status") != "done"]
    done_lanes = [l for l in lanes if l.get("status") == "done"]

    # 有 lane 被阻塞（优先级最高 —— 需要回 scope 重新拆解）
    blocked = [l for l in active_lanes if l.get("status") == "blocked"]
    if blocked:
        return LAND_BLOCKED

    # 有 lane 还在执行中（无 report）
    waiting = [l for l in active_lanes if not l.get("has_report")]
    if waiting:
        return LAND_WAITING

    # 有 lane 越界（boundary_pass 显式 False）
    boundary_failures = [l for l in done_lanes if l.get("boundary_pass") is False]
    if boundary_failures:
        return LAND_BOUNDARY

    # done lane 缺失证据 → 不能 land
    # report / test_results / boundary_pass 三者必须显式存在且为 True
    missing_report = [l for l in done_lanes if not l.get("has_report")]
    if missing_report:
        return LAND_WAITING

    missing_tests = [l for l in done_lanes if not l.get("has_test_results")]
    boundary_unknown = [l for l in done_lanes if l.get("boundary_pass") is None]

    all_done = len(active_lanes) == 0
    all_tested = len(missing_tests) == 0
    all_boundary_explicit = len(boundary_unknown) == 0

    if all_done and all_tested and all_boundary_explicit:
        return LAND_OK

    return LAND_WAITING


# ── Lane status aggregation (index.json + report.json → determine_land_status input) ─

# report.json 的契约格式（spawn_lane.py:186）
REPORT_REQUIRED_FIELDS = ["lane_id", "status", "changed_files", "test_results", "result"]

# 终态 status 值
TERMINAL_LANE_STATUSES = {"done", "blocked"}


def _default_report_reader(worktree_path: str) -> Optional[dict]:
    """默认 report reader：从 worktree 路径读 .splitrun/report.json。"""
    if not worktree_path:
        return None
    rp = Path(worktree_path) / ".splitrun" / "report.json"
    if not rp.exists():
        return None
    try:
        return json.loads(rp.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def aggregate_lane_status(
    index: dict,
    report_reader: Optional[Callable[[str], Optional[dict]]] = None,
) -> list[dict]:
    """从 lane index + report 聚合出 determine_land_status() 所需的 lane 状态列表。

    Args:
        index: lanes/index.json 的解析结果，格式为 {lane_id: {status, worktree, files_claimed, ...}}
        report_reader: 可注入的 report 读取函数，签名为 (worktree_path: str) -> dict | None。
                       默认从文件系统读 <worktree>/.splitrun/report.json。

    Returns:
        list[dict]，每条包含:
            lane_id, status, has_report, has_test_results, boundary_pass,
            changed_files, files_claimed, report_status
    """
    if report_reader is None:
        report_reader = _default_report_reader

    lanes = []
    for lane_id, entry in index.items():
        worktree = entry.get("worktree", "")
        files_claimed = entry.get("files_claimed", [])
        report = report_reader(worktree) if worktree else None

        if report:
            report_status = report.get("status", "blocked")
            changed_files = report.get("changed_files", [])
            test_results = report.get("test_results", "")

            # report 的 status 覆盖 index 的 status（report 是 ground truth）
            if report_status in TERMINAL_LANE_STATUSES:
                effective_status = report_status
            else:
                effective_status = entry.get("status", "active")

            # boundary check
            if changed_files:
                boundary_result = check_boundary(changed_files, files_claimed)
                boundary_pass = boundary_result["pass"]
            else:
                boundary_pass = None

            lanes.append({
                "lane_id": lane_id,
                "status": effective_status,
                "has_report": True,
                "has_test_results": bool(test_results),
                "boundary_pass": boundary_pass,
                "changed_files": changed_files,
                "files_claimed": files_claimed,
                "report_status": report_status,
            })
        else:
            # 无 report — 保留 index 中的原始状态
            lanes.append({
                "lane_id": lane_id,
                "status": entry.get("status", "active"),
                "has_report": False,
                "has_test_results": False,
                "boundary_pass": None,
                "changed_files": [],
                "files_claimed": files_claimed,
                "report_status": None,
            })

    return lanes
