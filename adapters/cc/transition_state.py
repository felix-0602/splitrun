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

# Profile 覆盖转移表
PROFILE_TRANSITION_OVERRIDES: dict[str, dict[str, set[str]]] = {
    "deployment": {
        "READ_CONTEXT": {"EXECUTE"},
    },
    "debug": {
        "READ_CONTEXT": {"MAP_REALITY"},
        "MAP_REALITY":  {"EXECUTE", "BLOCK"},
    },
}


def _get_profile_aware_transitions(active_profile: str) -> dict[str, set[str]]:
    """返回合并了 profile 覆盖的合法转移表。"""
    if not active_profile or active_profile == "development":
        return dict(LEGAL_TRANSITIONS)
    merged = dict(LEGAL_TRANSITIONS)
    overrides = PROFILE_TRANSITION_OVERRIDES.get(active_profile, {})
    for state, targets in overrides.items():
        merged[state] = targets
    return merged

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

        # rotate 门禁：上下文驱动（主要）+ counter 安全网（bridge file 不可用时）
        session_wu_count = state.get("_session_wu_count", 0)
        remaining = [w for w in wus if w.get("status") == "pending" and w["id"] != current_wu_id]
        context_critical = _is_context_critical()

        if context_critical:
            return False, (
                "上下文余量不足（剩余 ≤ 25%）——立即 rotate。"
                "运行: python adapters/parallel/rotate.py "
                "--diff-intent '<当前 diff>' --next-steps '<新会话下一步>'"
            )

        # 安全网：context monitor 不可用时，counter ≥ 6 强制保底 rotate
        if session_wu_count >= 6 and remaining:
            return False, (
                f"同一会话已完成 {session_wu_count} 个 WU（≥6），还有 {len(remaining)} 个待执行。"
                "context monitor 未触发但 counter 已达上限——为防止上下文溢出，请先 rotate 再继续。"
                "运行: python adapters/parallel/rotate.py "
                "--diff-intent '<当前 diff>' --next-steps '<新会话下一步>'"
            )

        # 标记 WU 为 in_progress，递增计数器
        if current_wu.get("status") == "pending":
            _set_wu_status(root, current_wu_id, "in_progress")
            state["_session_wu_count"] = session_wu_count + 1

    # → VALIDATE: 接受从 EXECUTE 或 REPAIR 进入。
    # 检查 review evidence（硬门禁）。inline WU 无 result.json 时从 WU 记录检查。
    if to_state == "VALIDATE":
        if current_wu:
            result_file = _find_result_file(current_wu_id) if current_wu_id else None
            result_data = None
            if result_file:
                try:
                    result_data = json.loads(result_file.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    pass
            review_ok, review_reason = _check_review_evidence(current_wu, result_data)
            if not review_ok:
                return False, review_reason
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
        # 跨 milestone 计数器归零：新 milestone 从 0 开始
        state["_session_wu_count"] = 0

    # → ADVANCE: 已启动的 WU（in_progress/done）必须 integrated + review 通过。pending 允许。
    # 然后检测自动续推：有 pending WU + continuation_mode=normal → 自动设 next_action。
    if to_state == "ADVANCE":
        if wus:
            not_integrated = [
                w["id"] for w in wus
                if w.get("status") in ("in_progress", "done", "blocked", "failed")
                and w.get("status") != "integrated"
            ]
            if not_integrated:
                return False, f"以下已启动 WU 未 integrated: {not_integrated}"

            # 检查 review evidence：所有非 pending WU 必须有 review
            missing_review = []
            for w in wus:
                if w.get("status") == "pending":
                    continue
                if w.get("status") == "integrated":
                    continue  # 已集成视为已通过审查
                result_file = _find_result_file(w["id"])
                result_data = None
                if result_file:
                    try:
                        result_data = json.loads(result_file.read_text(encoding="utf-8"))
                    except (json.JSONDecodeError, OSError):
                        pass
                review_ok, review_reason = _check_review_evidence(w, result_data)
                if not review_ok:
                    missing_review.append(review_reason)
            if missing_review:
                return False, f"review 门禁未通过: {'; '.join(missing_review)}"

            # ── 自动续推（block 纪律级别：强制执行，不允许跳过）──
            pending = [w for w in wus if w.get("status") == "pending"]
            if pending:
                ready = [w for w in pending if not _has_blocking_deps(w, wus)]
                if ready:
                    next_wu = ready[0]
                    cont_mode = current_wu.get("continuation_mode", "normal") if current_wu else "normal"
                    if cont_mode == "normal":
                        state["next_action"] = "continue_next_wu"
                        state["next_wu"] = next_wu["id"]
                        state["_pending_wu_count"] = len(pending)
                        print(
                            f"[ADVANCE] auto-continue: {current_wu_id} → {next_wu['id']} "
                            f"({len(pending)} pending WUs, continuation_mode=normal)"
                        )
                    else:
                        state["next_action"] = "await_user"
                        state["next_wu"] = next_wu["id"]
                        state["_pending_wu_count"] = len(pending)
                        print(
                            f"[ADVANCE] paused: continuation_mode={cont_mode}, "
                            f"{len(pending)} pending WUs, next={next_wu['id']}"
                        )
                else:
                    blocked = [w["id"] for w in pending if _has_blocking_deps(w, wus)]
                    state["next_action"] = "blocked_on_deps"
                    state["_blocked_wus"] = blocked
                    print(
                        f"[ADVANCE] blocked: {len(pending)} pending WUs, "
                        f"{len(blocked)} blocked by dependencies: {blocked}"
                    )
            else:
                state["next_action"] = "milestone_complete"
                state["_pending_wu_count"] = 0
                print(f"[ADVANCE] milestone complete: all {len(wus)} WUs integrated")

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


def _has_blocking_deps(wu: dict, all_wus: list[dict]) -> bool:
    """检查 WU 的 depends_on 中是否有未 integrated 的 WU。"""
    deps = wu.get("depends_on", [])
    if not deps:
        return False
    wu_map = {w["id"]: w for w in all_wus}
    for dep_id in deps:
        dep = wu_map.get(dep_id, {})
        if dep.get("status") != "integrated":
            return True
    return False


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


def _check_review_evidence(wu: dict, result: dict | None) -> tuple[bool, str]:
    """检查 WU 的 review 证据 — 硬门禁。

    risk_level=medium/high: 必须 review_status=passed
    risk_level=low: 必须 review_status 非空（passed/skipped），skipped 需理由
    """
    risk = wu.get("risk_level", "medium")

    # 优先从 result.json 取 review 字段，其次从 WU 记录
    review_status = None
    review_evidence = None
    if result:
        review_status = result.get("review_status")
        review_evidence = result.get("review_evidence")
    if not review_status:
        review_status = wu.get("review_status")
        review_evidence = wu.get("review_evidence")

    if not review_status:
        return False, f"{wu['id']}: 缺少 review_status（risk_level={risk}）"

    if review_status == "passed":
        if not review_evidence:
            return False, f"{wu['id']}: review_status=passed 但缺少 review_evidence"
        return True, ""

    if review_status == "skipped":
        if risk in ("medium", "high"):
            return False, f"{wu['id']}: risk_level={risk} 不允许跳过 review（仅 low 可豁免）"
        if not review_evidence:
            return False, f"{wu['id']}: review_status=skipped 但缺少豁免理由"
        return True, ""

    if review_status == "failed":
        return False, f"{wu['id']}: review 未通过 — {review_evidence or '无详细信息'}"

    return False, f"{wu['id']}: 未知 review_status: {review_status}"


def _is_context_critical() -> bool:
    """读取 gsd-context-monitor 的 bridge file，判断剩余上下文是否 ≤ 25%。"""
    import glob as _glob
    import os as _os
    import time as _time

    tmp = _os.environ.get("TMPDIR", _os.environ.get("TEMP", "/tmp"))
    now = _time.time()
    for f in _glob.glob(_os.path.join(tmp, "claude-ctx-*.json")):
        try:
            mtime = _os.path.getmtime(f)
            if now - mtime > 60:
                continue
            data = json.loads(Path(f).read_text(encoding="utf-8"))
            remaining = data.get("remaining_percentage", 100)
            if remaining <= 25:
                return True
        except (json.JSONDecodeError, OSError, KeyError):
            continue
    return False


def _archive_milestone(root: Path, state: dict, wus: list[dict]) -> None:
    """COMPLETE 时归档当前 milestone 的 work_units 快照到 .deepship/archive/。"""
    import shutil

    archive = root / ".deepship" / "archive"
    archive.mkdir(parents=True, exist_ok=True)
    milestone = state.get("current_milestone", "unknown")
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    src = root / ".deepship" / "work_units.json"
    dst = archive / f"milestone-{milestone}-{ts}.json"
    if src.exists():
        shutil.copy2(src, dst)
        print(f"[COMPLETE] 已归档 {len(wus)} 个 WU → {dst.name}")


def _clear_interrupt_flags(state: dict) -> None:
    """清除所有中断标记（类比 _rotation_pending 清除）。"""
    interrupt_keys = [
        "_interrupt_pending",
        "_interrupt_type",
        "_interrupt_received_at",
        "_interrupted_lane",
        "_interrupt_intent",
        "_interrupt_handled_at",
        "_interrupt_reconciliation",
    ]
    for key in interrupt_keys:
        state.pop(key, None)
    state["_session_wu_count"] = 0


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
        doc_path.parent.mkdir(parents=True, exist_ok=True)
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
    clear_rotation: bool = False,
    auto_recover: bool = False,
    clear_interrupt: bool = False,
) -> dict:
    """执行状态转移。返回 {"success": bool, "from": str, "to": str, "reason": str"}。"""
    root = project_root or _find_root()
    if root is None:
        return {"success": False, "reason": "未找到 .deepship/ 目录"}

    ctx = context or {}
    state = _load_state(root)
    wus = _load_work_units(root)
    from_state = state.get("current_state", "READ_CONTEXT")
    active_profile = state.get("active_profile", "development")

    # 0. --clear-rotation: 允许 READ_CONTEXT 和 PLAN_STEP（PLAN_STEP 可能因 rotate 门禁死锁）
    if clear_rotation:
        if from_state not in ("READ_CONTEXT", "PLAN_STEP"):
            return {
                "success": False,
                "from": from_state,
                "to": to_state,
                "reason": f"--clear-rotation 仅在 READ_CONTEXT 状态可用，当前: {from_state}。",
            }
        state.pop("_rotation_pending", None)
        state.pop("_rotated_at", None)
        state.pop("_rotated_from_wu", None)
        state["_session_wu_count"] = 0
        _write_state(root, state)
        _append_log(root, {
            "from_state": from_state,
            "to_state": from_state,
            "result": "ok",
            "reason": "rotation cleared — continuation.md 已确认读取",
            "current_work_unit": state.get("current_work_unit", ""),
        })
        return {
            "success": True,
            "from": from_state,
            "to": from_state,
            "reason": "已清除 _rotation_pending/_rotated_at/_rotated_from_wu。可以正常推进状态。",
        }

    # 0. --auto-recover: READ_CONTEXT 下一步到位（读 continuation.md + 清 rotation + claim ownership）
    if auto_recover:
        if from_state != "READ_CONTEXT":
            return {
                "success": False,
                "from": from_state,
                "to": to_state,
                "reason": f"--auto-recover 仅在 READ_CONTEXT 状态可用，当前: {from_state}。",
            }
        cont_path = root / ".deepship" / "continuation.md"
        cont_summary = ""
        if cont_path.exists():
            cont_summary = cont_path.read_text(encoding="utf-8")[:500]
        state.pop("_rotation_pending", None)
        state.pop("_rotated_at", None)
        state.pop("_rotated_from_wu", None)
        state["_session_wu_count"] = 0
        _write_state(root, state)

        # claim session ownership + 写 session_started_at 到 state.json
        # hook 用 state.session_started_at vs session.owner_started_at 做 generation 对比
        try:
            from adapters.session.session import SessionManager
            sm = SessionManager(root)
            sm.claim_ownership(root)
            session_data = sm._read()
            state["session_started_at"] = session_data.get("owner_started_at", "")
        except Exception:
            pass
        _write_state(root, state)

        _append_log(root, {
            "from_state": from_state,
            "to_state": from_state,
            "result": "ok",
            "reason": "auto-recover: rotation cleared + session ownership claimed",
            "current_work_unit": state.get("current_work_unit", ""),
        })
        return {
            "success": True,
            "from": from_state,
            "to": from_state,
            "reason": "auto-recover 完成：rotation cleared + session ownership claimed。",
            "continuation_summary": cont_summary or "(无 continuation.md)",
        }

    # 0. --clear-interrupt: 仅在 READ_CONTEXT 状态允许清除中断标记
    if clear_interrupt:
        if from_state != "READ_CONTEXT":
            return {
                "success": False,
                "from": from_state,
                "to": to_state,
                "reason": f"--clear-interrupt 仅在 READ_CONTEXT 状态可用，当前: {from_state}。",
            }
        _clear_interrupt_flags(state)
        _write_state(root, state)
        _append_log(root, {
            "from_state": from_state,
            "to_state": from_state,
            "result": "ok",
            "reason": "interrupt cleared — reconciliation complete",
            "current_work_unit": state.get("current_work_unit", ""),
        })
        return {
            "success": True,
            "from": from_state,
            "to": from_state,
            "reason": "已清除 _interrupt_pending/_interrupt_type/_interrupted_lane 等中断标记。可以正常推进状态。",
        }

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

    # 0. interrupt_pending 门禁：中断未处理时禁止进入 EXECUTE
    if to_state == "EXECUTE" and state.get("_interrupt_pending"):
        return {
            "success": False,
            "from": from_state,
            "to": to_state,
            "reason": "interrupt_pending=true——中断尚未处理。请先完成中断路由流程，执行 reconciliation 后再继续。",
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

    # 1. 校验合法转移（profile-aware）
    legal = _get_profile_aware_transitions(active_profile)
    allowed = legal.get(from_state, set())
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

    # 3.5 COMPLETE 时归档当前 milestone 的 work_units
    if to_state == "COMPLETE" and wus:
        _archive_milestone(root, state, wus)

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
  python adapters/cc/transition_state.py --clear-rotation
  python adapters/cc/transition_state.py --auto-recover
  python adapters/cc/transition_state.py --clear-interrupt
  python adapters/cc/transition_state.py --to REPAIR --context '{"validation_failed":true,"failure_reason":"test_auth failed"}'
  python adapters/cc/transition_state.py --to COMPLETE
        """,
    )
    parser.add_argument("--to", default="", help="目标状态（--clear-rotation/--auto-recover/--clear-interrupt 时不需要）")
    parser.add_argument("--wu", help="当前 Work Unit ID")
    parser.add_argument("--context", type=str, default="{}", help="上下文 JSON")
    parser.add_argument("--project-root", "-d", type=str, help="项目根目录")
    parser.add_argument("--clear-rotation", action="store_true", help="清除 _rotation_pending 标记（仅 READ_CONTEXT）")
    parser.add_argument("--auto-recover", action="store_true", help="旋转后自动恢复：清除 rotation + 读 continuation.md + claim session ownership")
    parser.add_argument("--clear-interrupt", action="store_true", help="清除 _interrupt_pending 等中断标记（仅 READ_CONTEXT）")

    args = parser.parse_args()

    if not args.to and not args.clear_rotation and not args.auto_recover and not args.clear_interrupt:
        print(json.dumps({"success": False, "reason": "需要 --to、--clear-rotation、--auto-recover 或 --clear-interrupt"}))
        sys.exit(1)

    try:
        ctx = json.loads(args.context)
    except json.JSONDecodeError:
        print(json.dumps({"success": False, "reason": "--context JSON 解析失败"}))
        sys.exit(1)

    root = Path(args.project_root) if args.project_root else None
    result = transition(
        to_state=args.to or "READ_CONTEXT",
        wu_id=args.wu,
        context=ctx,
        project_root=root,
        clear_rotation=args.clear_rotation,
        auto_recover=args.auto_recover,
        clear_interrupt=args.clear_interrupt,
    )

    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
