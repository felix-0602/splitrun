#!/usr/bin/env python3
"""
DEEPSHIP Transition State Tool — 纪律化的状态推进入口。

模型不该直接 Edit .deepship/state.json。通过此工具推进状态：
  python adapters/cc/transition_state.py --to EXECUTE --wu WU-001
  python adapters/cc/transition_state.py --to VALIDATE
  python adapters/cc/transition_state.py --to COMPLETE

职责：
  1. 校验合法转移（对照 protocol/state-machine.md 转移表）
  2. 校验守卫条件（Guard 条件）
  3. 写 .deepship/state.json
  4. 追加 .deepship/log.jsonl

输出 JSON 到 stdout，exit 0 = 成功，exit 1 = 失败。
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── 转移表（权威源：protocol/state-machine.md） ──────────

LEGAL_TRANSITIONS: dict[str, set[str]] = {
    "READ_CONTEXT":     {"CLARIFY_INTENT", "MAP_REALITY"},
    "CLARIFY_INTENT":   {"MAP_REALITY", "BLOCK"},
    "MAP_REALITY":      {"SELECT_MILESTONE", "BLOCK"},
    "SELECT_MILESTONE": {"PLAN_STEP", "BLOCK"},
    "PLAN_STEP":        {"EXECUTE"},
    "EXECUTE":          {"VALIDATE"},
    "VALIDATE":         {"RECORD", "REPAIR"},
    "REPAIR":           {"VALIDATE", "BLOCK"},
    "RECORD":           {"ADVANCE"},
    "ADVANCE":          {"READ_CONTEXT", "COMPLETE"},
    "BLOCK":            {"READ_CONTEXT"},
    "COMPLETE":         {"READ_CONTEXT"},
}

# ── Guard 条件 ──────────────────────────────────────────


def _set_wu_status(root: Path, wu_id: str, new_status: str) -> None:
    """更新 work_units.json 中指定 WU 的状态。"""
    wp = root / ".deepship" / "work_units.json"
    if not wp.exists():
        return
    data = json.loads(wp.read_text(encoding="utf-8"))
    for wu in data.get("work_units", []):
        if wu.get("id") == wu_id:
            wu["status"] = new_status
            wu["updated_at"] = datetime.now(timezone.utc).isoformat()
            break
    wp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _check_guard(
    root: Path,
    from_state: str,
    to_state: str,
    state: dict,
    wus: list[dict],
    context: dict,
) -> tuple[bool, str]:
    """校验转移的守卫条件。返回 (通过?, 原因)。"""
    current_wu_id = state.get("current_work_unit", "")
    wu_map = {w["id"]: w for w in wus}
    current_wu = wu_map.get(current_wu_id, {})

    # → EXECUTE: current_work_unit 非空，files_allowed 已定义
    if to_state == "EXECUTE":
        if not current_wu_id:
            return False, "current_work_unit 为空，无法进入 EXECUTE"
        if not current_wu.get("files_allowed"):
            return False, f"{current_wu_id} 的 files_allowed 为空"
        # 标记 WU 为 in_progress（写入 work_units.json）
        if current_wu.get("status") == "pending":
            _set_wu_status(root, current_wu_id, "in_progress")

    # → VALIDATE: 接受从 EXECUTE 或 REPAIR 进入
    if to_state == "VALIDATE":
        if context.get("acceptance_tests_ran") or _find_result_file(current_wu_id):
            return True, ""

    

    # → COMPLETE: 所有 WU integrated（或无 WU 文档任务）
    if to_state == "COMPLETE":
        if wus:
            not_integrated = [
                w["id"] for w in wus
                if w.get("status") != "integrated"
            ]
            if not_integrated:
                return False, f"以下 WU 未 integrated: {not_integrated}"

    # → ADVANCE: 已启动的 WU（in_progress/done）必须 integrated。pending 允许。
    if to_state == "ADVANCE":
        if wus:
            not_integrated = [
                w["id"] for w in wus
                if w.get("status") in ("in_progress", "done", "blocked", "failed")
                and w.get("status") != "integrated"
            ]
            if not_integrated:
                return False, f"以下已启动 WU 未 integrated: {not_integrated}"

    # → COMPLETE: 所有 WU integrated（或无 WU 纯文档任务）
    if to_state == "COMPLETE":
        if wus:
            not_integrated = [
                w["id"] for w in wus
                if w.get("status") != "integrated"
            ]
            if not_integrated:
                return False, f"以下 WU 未 integrated: {not_integrated}"

    # → REPAIR: VALIDATE 失败证据 + repair_count < 3
    if to_state == "REPAIR":
        if not context.get("validation_failed"):
            return False, "进入 REPAIR 需要 VALIDATE 失败证据（validation_failed=true）。"
        repair_count = state.get("repair_count", 0)
        if repair_count >= 3:
            return False, f"REPAIR 已达 {repair_count}/3 上限，应进入 BLOCK"

    return True, ""


def _find_result_file(wu_id: str) -> Path | None:
    """在项目目录下查找 WU 的 result.json。"""
    for candidate in [Path.cwd()] + list(Path.cwd().parents):
        result = candidate / ".deepship" / "runs" / wu_id / "result.json"
        if result.exists():
            return result
    return None


def _check_files_in_bounds(result: dict, wu: dict) -> bool:
    """检查 result.json 的 changed_files 是否在 WU 的 files_allowed 内。"""
    allowed = {a.replace("\\", "/").rstrip("/") for a in wu.get("files_allowed", [])}
    if not allowed:
        return True  # 未定义边界，跳过检查
    for f in result.get("changed_files", []):
        f_norm = f.replace("\\", "/")
        matched = any(
            f_norm == a or f_norm.startswith(a.rstrip("/") + "/")
            for a in allowed
        )
        if not matched:
            return False
    return True


# ── 状态读写 ────────────────────────────────────────────


def _find_root() -> Path | None:
    for candidate in [Path.cwd()] + list(Path.cwd().parents):
        if (candidate / ".deepship").is_dir():
            return candidate
    return None


def _load_state(root: Path) -> dict:
    sp = root / ".deepship" / "state.json"
    if sp.exists():
        return json.loads(sp.read_text(encoding="utf-8"))
    return {"current_state": "READ_CONTEXT"}


def _load_work_units(root: Path) -> list[dict]:
    wp = root / ".deepship" / "work_units.json"
    if wp.exists():
        data = json.loads(wp.read_text(encoding="utf-8"))
        return data.get("work_units", [])
    return []


def _write_state(root: Path, state: dict) -> None:
    sp = root / ".deepship" / "state.json"
    sp.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    sp.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _append_log(root: Path, entry: dict) -> None:
    lp = root / ".deepship" / "log.jsonl"
    lp.parent.mkdir(parents=True, exist_ok=True)
    entry["timestamp"] = datetime.now(timezone.utc).isoformat()
    with open(lp, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def write_pending_record(root: Path, event_type: str, message: str, context: dict | None = None) -> None:
    """在 EXECUTE/REPAIR 中途合规记录事件。追加到 pending_records.jsonl，RECORD 时回收。"""
    pr = root / ".deepship" / "pending_records.jsonl"
    pr.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "message": message,
        "context": context or {},
    }
    with open(pr, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _recover_pending_records(root: Path) -> list[dict]:
    """RECORD 时回收 pending_records.jsonl，返回已回收的记录列表，清空文件。"""
    pr = root / ".deepship" / "pending_records.jsonl"
    if not pr.exists():
        return []
    records = []
    with open(pr, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    # 追加到 Documentation.md（如果存在）
    if records:
        doc_path = root / ".claude" / "DEEPSHIP" / "Documentation.md"
        if not doc_path.exists():
            doc_path = root / "Documentation.md"
        if doc_path.exists():
            with open(doc_path, "a", encoding="utf-8") as f:
                f.write(f"\n### 待定记录回收 — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}\n\n")
                for r in records:
                    f.write(f"- **{r['event_type']}**: {r['message']}\n")
    # 清空文件
    pr.write_text("", encoding="utf-8")
    return records


# ── 主逻辑 ──────────────────────────────────────────────


def transition(
    to_state: str,
    wu_id: str | None = None,
    context: dict | None = None,
    project_root: Path | None = None,
) -> dict:
    """执行状态转移。返回 {"success": bool, "from": str, "to": str, "reason": str}。"""
    root = project_root or _find_root()
    if root is None:
        return {"success": False, "reason": "未找到 .deepship/ 目录"}

    ctx = context or {}
    state = _load_state(root)
    wus = _load_work_units(root)
    from_state = state.get("current_state", "READ_CONTEXT")

    # 更新 state 中的 WU 引用
    if wu_id:
        state["current_work_unit"] = wu_id

    # 0. rotation_pending 门禁：新会话必须先确认 continuation 已读
    if to_state == "EXECUTE" and state.get("_rotation_pending"):
        return {
            "success": False,
            "from": from_state,
            "to": to_state,
            "reason": "rotation_pending=true——新会话必须先 READ_CONTEXT 读取 continuation.md，确认后清除 _rotation_pending 再进 EXECUTE。",
        }

    # 0. fork 门禁：有 fork WU 未回收时不能从 EXECUTE 直接到 VALIDATE
    if to_state == "VALIDATE" and from_state == "EXECUTE":
        fork_wus_in_flight = [
            w for w in wus
            if w.get("execution_mode") == "fork"
            and w.get("status") in ("in_progress", "done")
        ]
        # 检查是否有 collector evidence
        if fork_wus_in_flight:
            for fw in fork_wus_in_flight:
                result = _find_result_file(fw["id"])
                if not result:
                    return {
                        "success": False,
                        "from": from_state,
                        "to": to_state,
                        "reason": f"fork WU {fw['id']} 没有 result.json——fork 必须经过 collector 回收。请运行 collector.py。",
                    }
                # 边界校验：changed_files ⊆ files_allowed
                try:
                    data = json.loads(result.read_text(encoding="utf-8"))
                    if not _check_files_in_bounds(data, fw):
                        return {
                            "success": False,
                            "from": from_state,
                            "to": to_state,
                            "reason": f"fork WU {fw['id']} 的 changed_files 越界。",
                        }
                except (json.JSONDecodeError, OSError):
                    pass  # 格式问题由 collector 处理

    # 1. 校验合法转移
    allowed = LEGAL_TRANSITIONS.get(from_state, set())
    if to_state not in allowed:
        legal = ", ".join(sorted(allowed)) if allowed else "（终态）"
        return {
            "success": False,
            "from": from_state,
            "to": to_state,
            "reason": f"非法转移: {from_state} → {to_state}。合法目标: {legal}",
        }

    # 2. 校验 Guard 条件
    ok, reason = _check_guard(root, from_state, to_state, state, wus, ctx)
    if not ok:
        return {
            "success": False,
            "from": from_state,
            "to": to_state,
            "reason": f"Guard 未通过: {reason}",
        }

    # 3. RECORD 时回收 pending records
    if to_state == "RECORD":
        recovered = _recover_pending_records(root)
        if recovered:
            print(f"[RECORD] 已回收 {len(recovered)} 条 pending records 到 Documentation.md")

    # 4. 更新状态
    old_state = dict(state)
    state["current_state"] = to_state

    # 状态进入/退出时的附加逻辑
    if to_state == "REPAIR":
        state["repair_count"] = state.get("repair_count", 0) + 1
        state["repair_reason"] = ctx.get("failure_reason", "")
    elif to_state == "VALIDATE":
        pass  # VALIDATE 从 EXECUTE 或 REPAIR 进入时不重置 repair_count
    elif to_state != "REPAIR":
        # 离开 REPAIR- VALIDATE 循环时重置计数
        if from_state not in ("REPAIR", "VALIDATE"):
            state.pop("repair_count", None)

    # 4. 写入
    _write_state(root, state)

    # 5. 记录日志
    _append_log(root, {
        "from_state": from_state,
        "to_state": to_state,
        "result": "ok",
        "reason": reason or f"转移成功: {from_state} → {to_state}",
        "current_work_unit": state.get("current_work_unit", ""),
        "context": ctx,
    })

    return {
        "success": True,
        "from": from_state,
        "to": to_state,
        "reason": reason or f"转移成功: {from_state} → {to_state}",
        "wu": state.get("current_work_unit", ""),
    }


# ── CLI ─────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="DEEPSHIP Transition State — 纪律化状态推进",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
示例:
  python adapters/cc/transition_state.py --to EXECUTE --wu WU-001
  python adapters/cc/transition_state.py --to VALIDATE
  python adapters/cc/transition_state.py --to REPAIR --context '{"validation_failed":true,"failure_reason":"test_auth failed"}'
  python adapters/cc/transition_state.py --to COMPLETE
        """,
    )
    parser.add_argument("--to", required=True, help="目标状态")
    parser.add_argument("--wu", help="当前 Work Unit ID")
    parser.add_argument("--context", type=str, default="{}", help="上下文 JSON")
    parser.add_argument("--project-root", "-d", type=str, help="项目根目录")

    args = parser.parse_args()

    try:
        ctx = json.loads(args.context)
    except json.JSONDecodeError:
        print(json.dumps({"success": False, "reason": "--context JSON 解析失败"}))
        sys.exit(1)

    root = Path(args.project_root) if args.project_root else None
    result = transition(
        to_state=args.to,
        wu_id=args.wu,
        context=ctx,
        project_root=root,
    )

    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
