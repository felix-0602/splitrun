#!/usr/bin/env python3
"""
SPLIT-RUN Session Rotator v0.2 — 自旋转：保存 checkpoint → 开新终端继续.

由模型在执行中的安全点调用。
新会话通过 READ_CONTEXT 读取 continuation.md + --auto-recover 接上。

v0.2:
  - --kill-old: 平台检测并尝试杀旧终端（Windows: taskkill, Unix: pkill）
  - continuation.md 模板更新为新旧会话处置指南
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# 支持直接执行或模块导入
from adapters.parallel._utils import (
        SPLITRUN_DIR,
        find_splitrun_root,
        _check_wt_available,
        _validate_wu_id,
    )

# ── continuation.md 模板 ─────────────────────────────────

CONTINUATION_TEMPLATE = """\
# 旋转点 — {timestamp}

## 我在哪
- 状态机: {current_state}
- 当前 WU: {current_wu}（{wu_status}）
- 下一个 WU: {next_wu}

## 已完成
{completed}

## 当前 diff 意图
{diff_intent}

## 下一步必须做
{next_steps}

## 注意事项
{notes}

## 新会话恢复
新会话 READ_CONTEXT 读取本文件后，执行自动恢复：
  python adapters/cc/transition_state.py --auto-recover
这会清除旋转标记 + 重置 WU 计数器 + claim session ownership。

## 旧会话处置
{old_session_guide}
"""


# ── 状态读取 ────────────────────────────────────────────


def _load_state(root: Path) -> dict:
    state_path = root / SPLITRUN_DIR / "state.json"
    if state_path.exists():
        return json.loads(state_path.read_text(encoding="utf-8"))
    return {}


def _load_work_units(root: Path) -> list[dict]:
    wu_path = root / SPLITRUN_DIR / "work_units.json"
    if wu_path.exists():
        data = json.loads(wu_path.read_text(encoding="utf-8"))
        return data.get("work_units", [])
    return []


def _get_current_wu_info(root: Path) -> dict:
    """读取当前状态，返回 continuation.md 所需信息。"""
    state = _load_state(root)
    wus = _load_work_units(root)

    current_wu_id = state.get("current_work_unit", "?")
    current_state = state.get("current_state", "READ_CONTEXT")

    wu_map = {w["id"]: w for w in wus}
    current_wu = wu_map.get(current_wu_id, {})

    # 找下一个 pending WU
    pending = [w for w in wus if w.get("status") == "pending"]
    next_wu = pending[0]["id"] if pending else "none"

    return {
        "current_state": current_state,
        "current_wu": current_wu_id,
        "wu_status": current_wu.get("status", "?"),
        "wu_goal": current_wu.get("goal", "?"),
        "next_wu": next_wu,
        "wus": wus,
    }


# ── continuation.md 写入 ─────────────────────────────────


def write_continuation(
    root: Path,
    diff_intent: str = "（见 git diff）",
    completed: str = "",
    next_steps: str = "1. 运行 READ_CONTEXT 读取 state.json 和 continuation.md\n2. 接上状态机继续执行\n",
    notes: str = "（无特殊注意事项）",
    old_session_guide: str = "",
) -> Path:
    """写入 .splitrun/continuation.md，返回文件路径。"""
    info = _get_current_wu_info(root)

    if not completed:
        completed_lines = []
        for w in info["wus"]:
            if w.get("status") in ("done", "integrated"):
                completed_lines.append(f"- {w['id']}: {w.get('goal', '?')} — {w['status']}")
        completed = "\n".join(completed_lines) if completed_lines else "（暂无已完成的 WU）"

    if diff_intent == "（见 git diff）":
        try:
            diff_result = subprocess.run(
                ["git", "-C", str(root), "diff", "--stat", "HEAD"],
                capture_output=True, text=True, timeout=10,
            )
            if diff_result.stdout.strip():
                diff_intent = "```\n" + diff_result.stdout.strip()[:2000] + "\n```"
        except Exception:
            pass

    if not old_session_guide:
        old_session_guide = _build_old_session_guide(kill_old=False)

    content = CONTINUATION_TEMPLATE.format(
        timestamp=datetime.now(timezone.utc).isoformat(),
        current_state=info["current_state"],
        current_wu=info["current_wu"],
        wu_status=info["wu_status"],
        next_wu=info["next_wu"],
        completed=completed,
        diff_intent=diff_intent,
        next_steps=next_steps,
        notes=notes,
        old_session_guide=old_session_guide,
    )

    cont_path = root / SPLITRUN_DIR / "continuation.md"
    cont_path.write_text(content, encoding="utf-8")
    print(f"[ROTATE] continuation.md 已写入: {cont_path}")
    return cont_path


# ── 旧会话处置 ──────────────────────────────────────────

def kill_old_session() -> dict:
    """平台检测，尝试杀旧终端进程。返回 {'killed': bool, 'platform': str, 'detail': str}。"""
    system = platform.system()
    result = {"killed": False, "platform": system, "detail": ""}

    if system == "Windows":
        # taskkill 当前控制台进程树
        try:
            pid = os.getppid()
            proc = subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                capture_output=True, text=True, timeout=15,
            )
            result["detail"] = proc.stdout.strip() or proc.stderr.strip()
            result["killed"] = proc.returncode == 0
        except Exception as e:
            result["detail"] = str(e)
    elif system in ("Linux", "Darwin"):
        # 杀父 shell 及其子进程
        try:
            ppid = os.getppid()
            proc = subprocess.run(
                ["pkill", "-P", str(ppid)],
                capture_output=True, text=True, timeout=15,
            )
            result["detail"] = proc.stdout.strip() or proc.stderr.strip()
            result["killed"] = proc.returncode == 0
        except Exception as e:
            result["detail"] = str(e)
    else:
        result["detail"] = f"不支持的操作系统: {system}"

    return result


def _build_old_session_guide(kill_old: bool = False) -> str:
    """构建旧会话处置指南文本。"""
    guide = ""

    if kill_old:
        kill_result = kill_old_session()
        if kill_result["killed"]:
            guide = f"已通过平台检测 ({kill_result['platform']}) 杀旧终端进程。\n详情: {kill_result['detail']}"
        else:
            guide = (f"平台检测 ({kill_result['platform']}) 杀旧终端失败。\n"
                     f"详情: {kill_result['detail']}\n"
                     "请手动关闭旧终端窗口，避免双会话并行冲突。")
    else:
        guide = ("旋转后旧终端仍在运行。建议操作：\n"
                 "1. 关闭旧终端窗口\n"
                 "2. 或在旧终端执行 `exit`\n"
                 "3. 如已丢失旧终端，新会话的 --auto-recover + session ownership 可防止旧会话写入")

    return guide


# ── 新终端启动 ──────────────────────────────────────────


def spawn_new_session(root: Path) -> subprocess.Popen | None:
    """打开新 Windows Terminal 标签页，运行 claude 在项目目录。"""
    if not _check_wt_available():
        print("[ROTATE] wt.exe 不可用，无法启动新终端。")
        print(f"         请手动在项目目录运行: claude")
        return None

    session_id = str(uuid.uuid4())
    title = f"splitrun-continue"

    cmd = [
        "wt.exe", "--title", title,
        "-d", str(root),
        "powershell", "-NoExit", "-Command",
        f"claude --name splitrun-continue --session-id {session_id} --model sonnet",
    ]

    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"[ROTATE] 新终端已启动  session={session_id[:8]}...")
        print(f"[ROTATE] 新会话启动后自动 READ_CONTEXT → 读 continuation.md → 接上状态机")
        print(f"[ROTATE] 本条对话可以关闭。")
        return proc
    except FileNotFoundError:
        print(f"[ROTATE] 启动失败 —— wt.exe 未找到")
        return None


# ── 主入口 ──────────────────────────────────────────────


def rotate(
    project_root: Path | None = None,
    diff_intent: str = "",
    completed: str = "",
    next_steps: str = "",
    notes: str = "",
    no_spawn: bool = False,
    kill_old: bool = False,
) -> Path | None:
    """主入口：写 continuation.md → 开新终端。

    返回 continuation.md 路径。
    kill_old=True 时尝试平台检测杀旧终端。
    """
    root = project_root or find_splitrun_root()
    if root is None:
        print("[ERROR] 未找到 .splitrun/ 目录。")
        sys.exit(1)

    print(f"[ROTATE] 项目: {root}")

    info = _get_current_wu_info(root)

    # 硬门禁：只有 rotatable WU 才能旋转
    current_wu_id = info["current_wu"]
    if current_wu_id == "?":
        print("[ROTATE] 无法确定当前 WU，中止。请先确认 state.json 中的 current_work_unit。")
        sys.exit(1)

    wu_map = {w["id"]: w for w in info["wus"]}
    wu = wu_map.get(current_wu_id, {})
    exec_mode = wu.get("execution_mode", "inline")
    cont_mode = wu.get("continuation_mode", "normal")

    if cont_mode != "rotatable":
        print(f"[ROTATE] 拒绝: {current_wu_id} 的 continuation_mode={cont_mode}，不是 rotatable。")
        print(f"         只有 PLAN_STEP 标记 continuation_mode=rotatable 的 WU 才能旋转。")
        print(f"         如果确实需要，请先在 work_units.json 中改为 rotatable 后重试。")
        sys.exit(1)

    if exec_mode == "inline":
        print(f"[ROTATE] 拒绝: {current_wu_id} 的 execution_mode=inline。inline 任务不旋转。")
        sys.exit(1)

    # checkpoint 质量：diff_intent 和 next_steps 必须非空
    if not diff_intent or diff_intent == "（见 git diff）":
        print("[ROTATE] 拒绝: --diff-intent 不能为空。请描述当前改动的意图。")
        print("         用法: python rotate.py --diff-intent '重构了 token 验证逻辑'")
        sys.exit(1)

    if not next_steps or next_steps == "1. READ_CONTEXT 读 state.json + continuation.md\n2. 接上状态机继续执行\n":
        print("[ROTATE] 拒绝: --next-steps 不能为空。请写明下一步必须做什么。")
        print("         用法: python rotate.py --next-steps '1. pytest tests/ -v\\n2. VALIDATE'")
        sys.exit(1)

    print(f"[ROTATE] 状态: {info['current_state']}, WU: {current_wu_id} ({info['wu_status']})")

    # 写 continuation.md
    old_session_guide = _build_old_session_guide(kill_old=kill_old)
    cont_path = write_continuation(
        root,
        diff_intent=diff_intent or "（见 git diff）",
        completed=completed,
        next_steps=next_steps or "1. READ_CONTEXT 读 state.json + continuation.md\n2. 接上状态机继续执行\n",
        notes=notes or "（无特殊注意事项）",
        old_session_guide=old_session_guide,
    )

    # 更新 state.json：标记旋转 + rotation_pending 门禁
    state = _load_state(root)
    if state:
        state["_rotated_at"] = datetime.now(timezone.utc).isoformat()
        state["_rotated_from_wu"] = current_wu_id
        state["_rotation_pending"] = True
        state_path = root / SPLITRUN_DIR / "state.json"
        state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

    if no_spawn:
        print(f"[ROTATE] --no-spawn: 仅写入 continuation.md，不启动新终端。")
        print(f"         手动继续: cd {root} && claude")
        return cont_path

    spawn_new_session(root)
    return cont_path


# ── CLI ─────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="SPLIT-RUN Session Rotator v0.2 —— 保存 checkpoint + 启动新终端继续",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
示例:
  python adapters/parallel/rotate.py --diff-intent "重构了 token 验证" --next-steps "1. pytest 2. VALIDATE"
  python adapters/parallel/rotate.py --no-spawn
  python adapters/parallel/rotate.py --kill-old --diff-intent "重构了 token 验证" --next-steps "1. pytest"
        """,
    )
    parser.add_argument("--project-root", "-d", type=str, help="项目根目录（默认：自动检测）")
    parser.add_argument("--diff-intent", type=str, default="", help="当前 diff 的意图描述")
    parser.add_argument("--completed", type=str, default="", help="已完成工作的描述")
    parser.add_argument("--next-steps", type=str, default="", help="下一步必须做的操作")
    parser.add_argument("--notes", type=str, default="", help="注意事项（坑/已知问题）")
    parser.add_argument("--no-spawn", action="store_true", help="只写 continuation.md，不启动新终端")
    parser.add_argument("--kill-old", action="store_true", help="尝试平台检测杀旧终端进程（Windows: taskkill, Unix: pkill）")

    args = parser.parse_args()

    root = Path(args.project_root) if args.project_root else None
    rotate(
        project_root=root,
        diff_intent=args.diff_intent,
        completed=args.completed,
        next_steps=args.next_steps,
        notes=args.notes,
        no_spawn=args.no_spawn,
        kill_old=args.kill_old,
    )


if __name__ == "__main__":
    main()
