#!/usr/bin/env python3
"""
DEEPSHIP Session Rotator v0.1 — 自旋转：保存 checkpoint → 开新终端继续.

由模型在执行中的安全点调用。不杀当前进程，只开新终端。
新会话通过 READ_CONTEXT 读取 continuation.md 自然接上。
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# 支持直接执行或模块导入
try:
    from adapters.parallel.dispatcher import (
        DEEPSHIP_DIR,
        find_deepship_root,
        _check_wt_available,
        _validate_wu_id,
    )
except ModuleNotFoundError:
    _here = Path(__file__).resolve().parents[2]
    if str(_here) not in sys.path:
        sys.path.insert(0, str(_here))
    from adapters.parallel.dispatcher import (
        DEEPSHIP_DIR,
        find_deepship_root,
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
"""


# ── 状态读取 ────────────────────────────────────────────


def _load_state(root: Path) -> dict:
    state_path = root / DEEPSHIP_DIR / "state.json"
    if state_path.exists():
        return json.loads(state_path.read_text(encoding="utf-8"))
    return {}


def _load_work_units(root: Path) -> list[dict]:
    wu_path = root / DEEPSHIP_DIR / "work_units.json"
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
) -> Path:
    """写入 .deepship/continuation.md，返回文件路径。"""
    info = _get_current_wu_info(root)

    # 自动生成 completed（如果没给）
    if not completed:
        completed_lines = []
        for w in info["wus"]:
            if w.get("status") in ("done", "integrated"):
                completed_lines.append(f"- {w['id']}: {w.get('goal', '?')} — {w['status']}")
        completed = "\n".join(completed_lines) if completed_lines else "（暂无已完成的 WU）"

    # 如果没有提供 diff_intent，尝试从 git 获取
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
    )

    cont_path = root / DEEPSHIP_DIR / "continuation.md"
    cont_path.write_text(content, encoding="utf-8")
    print(f"[ROTATE] continuation.md 已写入: {cont_path}")
    return cont_path


# ── 新终端启动 ──────────────────────────────────────────


def spawn_new_session(root: Path) -> subprocess.Popen | None:
    """打开新 Windows Terminal 标签页，运行 claude 在项目目录。"""
    if not _check_wt_available():
        print("[ROTATE] wt.exe 不可用，无法启动新终端。")
        print(f"         请手动在项目目录运行: claude")
        return None

    session_id = str(uuid.uuid4())
    title = f"deepship-continue"

    cmd = [
        "wt.exe", "--title", title,
        "-d", str(root),
        "powershell", "-NoExit", "-Command",
        f"claude --name deepship-continue --session-id {session_id} --model sonnet",
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
) -> Path | None:
    """主入口：写 continuation.md → 开新终端。

    返回 continuation.md 路径，如果 no_spawn 则不开终端。
    """
    root = project_root or find_deepship_root()
    if root is None:
        print("[ERROR] 未找到 .deepship/ 目录。")
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
    cont_path = write_continuation(
        root,
        diff_intent=diff_intent or "（见 git diff）",
        completed=completed,
        next_steps=next_steps or "1. READ_CONTEXT 读 state.json + continuation.md\n2. 接上状态机继续执行\n",
        notes=notes or "（无特殊注意事项）",
    )

    # 更新 state.json：标记旋转 + rotation_pending 门禁
    state = _load_state(root)
    if state:
        state["_rotated_at"] = datetime.now(timezone.utc).isoformat()
        state["_rotated_from_wu"] = current_wu_id
        state["_rotation_pending"] = True
        state_path = root / DEEPSHIP_DIR / "state.json"
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
        description="DEEPSHIP Session Rotator v0.1 —— 保存 checkpoint + 启动新终端继续",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
示例:
  python adapters/parallel/rotate.py
  python adapters/parallel/rotate.py --no-spawn
  python adapters/parallel/rotate.py --diff-intent "重构了 token 验证" --notes "test_logout 偶发失败"
        """,
    )
    parser.add_argument(
        "--project-root", "-d", type=str,
        help="项目根目录（默认：自动检测）",
    )
    parser.add_argument(
        "--diff-intent", type=str, default="",
        help="当前 diff 的意图描述",
    )
    parser.add_argument(
        "--completed", type=str, default="",
        help="已完成工作的描述",
    )
    parser.add_argument(
        "--next-steps", type=str, default="",
        help="下一步必须做的操作",
    )
    parser.add_argument(
        "--notes", type=str, default="",
        help="注意事项（坑/已知问题）",
    )
    parser.add_argument(
        "--no-spawn", action="store_true",
        help="只写 continuation.md，不启动新终端",
    )

    args = parser.parse_args()

    root = Path(args.project_root) if args.project_root else None
    rotate(
        project_root=root,
        diff_intent=args.diff_intent,
        completed=args.completed,
        next_steps=args.next_steps,
        notes=args.notes,
        no_spawn=args.no_spawn,
    )


if __name__ == "__main__":
    main()
