#!/usr/bin/env python3
"""
DEEPSHIP Claude Code Adapter — PreToolUse Gate Hook

读取 .deepship/state.json + work_units.json，执行策略门禁。
返回 CC hooks 兼容的 JSON 到 stdout。

安装方式：
1. cp deepship_gate.py ~/.claude/DEEPSHIP/adapters/cc/hooks/
2. 在 settings.json 注册：
   {
     "hooks": {
       "PreToolUse": [{
         "matcher": "Edit|Write|Bash",
         "hooks": [{"type": "command", "command": "python ~/.claude/DEEPSHIP/adapters/cc/hooks/deepship_gate.py", "timeout": 5}]
       }]
     }
   }

协议兼容：直接使用 DEEPSHIP tests/conformance/policy_cases.json 的策略逻辑。
"""
import json
import sys
from pathlib import Path


# ── 策略常量（与 tests/conformance/policy_cases.json 对齐） ──

MUTATING_TOOLS = {"edit", "write", "bash", "multiedit", "write_file", "edit_file"}
READONLY_TOOLS = {"read", "grep", "glob", "task", "skill", "read_file"}
TRANSITION_TOOLS = {"transitionstate", "transition_state"}

EXECUTE_STATES = {"EXECUTE", "REPAIR"}

# 文件分类
DEEPSHIP_STATE_FILES = ["state.json", "work_units.json", "log.jsonl"]
PROJECT_DOC_FILES = ["Documentation.md", "CHANGELOG.md", "README.md", "Prompt.md", "Plan.md"]
DOC_SUFFIXES = (".md",)


def load_deepship_state() -> dict:
    """从当前工作目录加载 DEEPSHIP 状态"""
    for root_candidate in [Path.cwd()] + list(Path.cwd().parents):
        state_path = root_candidate / ".deepship" / "state.json"
        if state_path.exists():
            return json.loads(state_path.read_text(encoding="utf-8"))
    return {}


def load_work_units() -> list[dict]:
    for root_candidate in [Path.cwd()] + list(Path.cwd().parents):
        wu_path = root_candidate / ".deepship" / "work_units.json"
        if wu_path.exists():
            data = json.loads(wu_path.read_text(encoding="utf-8"))
            return data.get("work_units", [])
    return []


def get_current_work_unit(state: dict, wus: list) -> dict | None:
    wu_id = state.get("current_work_unit", "")
    if not wu_id:
        return None
    for wu in wus:
        if wu.get("id") == wu_id:
            return wu
    return None


def path_in_workspace(file_path: str, workspace: str | None) -> bool:
    if not workspace or not file_path:
        return True
    normalized_file = file_path.replace("\\", "/").rstrip("/")
    normalized_ws = workspace.replace("\\", "/").rstrip("/")
    return normalized_file == normalized_ws or normalized_file.startswith(normalized_ws + "/")


def _write_kind(file_path: str, root: str | None) -> str:
    """分类写入目标：state_write / doc_write / code_write。"""
    fp = file_path.replace("\\", "/")

    # .deepship/ 下的元数据文件
    if ".deepship/" in fp:
        for sf in DEEPSHIP_STATE_FILES:
            if fp.endswith("/" + sf) or fp.endswith(sf):
                return "state_write"
        # .deepship/runs/ 下的 result.json 也是元数据
        if "/runs/" in fp and fp.endswith(".json"):
            return "state_write"
        # .deepship/ 下其他文件（continuation.md 等）视为 doc
        return "doc_write"

    # 项目文档
    for df in PROJECT_DOC_FILES:
        if fp.endswith(df) or fp.endswith("/" + df):
            return "doc_write"
    if fp.endswith(DOC_SUFFIXES):
        # .md 文件在项目根目录或 docs/ 下视为文档
        if "/docs/" in fp or fp.count("/") <= 1:
            return "doc_write"

    # 其他一切是项目代码
    return "code_write"


def evaluate(tool_name: str, args: dict, state: dict, wu: dict | None) -> tuple[bool, str]:
    """DEEPSHIP 策略评估（写分类 + 阶段门禁）。"""
    current_state = state.get("current_state", "READ_CONTEXT")
    tool_key = tool_name.lower()

    # Gate 0: COMPLETE 终态
    if current_state == "COMPLETE":
        return False, "COMPLETE 是终态，不允许工具调用"

    # Gate 1: 只读放行
    if tool_key in READONLY_TOOLS:
        return True, "只读工具不受门禁"

    # Gate 2: 状态转移 —— 放行 transition_state 工具
    if tool_key in TRANSITION_TOOLS:
        return True, "transition_state 工具由自身校验合法转移"

    # Gate 3: Bash 命令——在 VALIDATE / EXECUTE / REPAIR 放行
    if tool_key == "bash":
        if current_state in ("VALIDATE", "EXECUTE", "REPAIR", "RECORD"):
            return True, f"{current_state} 允许 Bash"
        if current_state == "READ_CONTEXT":
            cmd = str(args.get("command", "")).strip()
            if cmd.startswith("git status") or cmd.startswith("git diff") or cmd.startswith("git log"):
                return True, "READ_CONTEXT 允许 git 只读命令"
        return False, f"{current_state} 不允许 Bash。推进到 EXECUTE 后执行命令。"

    # Gate 4: 写入工具 —— 先分类再按状态放行
    if tool_key in ("edit", "write", "multiedit", "write_file", "edit_file"):
        fp = args.get("file_path", "")
        kind = _write_kind(fp, state.get("workspace"))
        workspace = state.get("workspace")

        # 工作区边界
        if not path_in_workspace(fp, workspace):
            return False, f"文件 {fp} 不在 workspace {workspace} 内"

        # ── 按状态 + 写分类放行 ──

        if current_state == "READ_CONTEXT":
            if kind == "state_write":
                return True, f"READ_CONTEXT 允许初始化 state 文件: {fp}"
            if kind == "doc_write":
                return True, f"READ_CONTEXT 允许创建文档: {fp}"
            return False, "READ_CONTEXT 不能改项目代码。先 MAP_REALITY → PLAN_STEP。"

        if current_state in ("CLARIFY_INTENT", "MAP_REALITY"):
            if kind in ("state_write", "doc_write"):
                return True, f"{current_state} 允许写 state/doc: {fp}"
            return False, f"{current_state} 不能改代码。"

        if current_state == "SELECT_MILESTONE":
            if kind == "state_write":
                return True, f"SELECT_MILESTONE 允许写 WU 结构: {fp}"
            if kind == "doc_write":
                return True, f"SELECT_MILESTONE 允许写计划文档: {fp}"
            return False, "SELECT_MILESTONE 不能改代码。"

        if current_state == "PLAN_STEP":
            if kind == "state_write":
                return True, f"PLAN_STEP 允许写 work_units.json: {fp}"
            if kind == "doc_write":
                return True, f"PLAN_STEP 允许写计划文档: {fp}"
            return False, "PLAN_STEP 只产出 WU 和计划文档，不改项目代码。"

        if current_state in EXECUTE_STATES:
            if kind == "state_write":
                return False, f"{current_state} 不能改元数据。用 transition_state.py 推进状态，用 RECORD 写集成结果。"
            if kind == "code_write":
                # WU 边界检查
                if wu:
                    allowed = wu.get("files_allowed", [])
                    if allowed:
                        matched = any(
                            fp == a.replace("\\", "/")
                            or fp.startswith(a.replace("\\", "/").rstrip("/*") + "/")
                            for a in allowed
                        )
                        if not matched:
                            return False, f"文件 {fp} 不在当前 WU files_allowed 中"
                return True, f"{current_state} 允许改代码: {fp}"
            # EXECUTE 中的 doc_write
            return True, f"{current_state} 允许写文档: {fp}"

        if current_state == "VALIDATE":
            if kind in ("state_write", "doc_write"):
                return True, f"VALIDATE 允许记录验证结果: {fp}"
            return False, "VALIDATE 阶段不能改代码。失败请用 transition_state.py --to REPAIR。"

        if current_state == "RECORD":
            if kind in ("state_write", "doc_write"):
                return True, f"RECORD 允许写状态和文档: {fp}"
            return False, "RECORD 阶段不能改代码。集成完成后用 transition_state.py --to ADVANCE。"

        if current_state == "ADVANCE":
            if kind in ("state_write", "doc_write"):
                return True, f"ADVANCE 允许写状态和交付总结: {fp}"
            return False, "ADVANCE 不能改代码。"

        if current_state == "BLOCK":
            if kind == "doc_write":
                return True, f"BLOCK 允许记录阻塞原因: {fp}"
            return False, "BLOCK 只能写文档记录阻塞原因。"

    return True, "允许"


# ── CC Hook 入口 ────────────────────────────────────

def main():
    try:
        input_data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        print(json.dumps({"hookSpecificOutput": {"permissionDecision": "allow"}}))
        return

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})
    args = tool_input if isinstance(tool_input, dict) else {}

    state = load_deepship_state()
    wus = load_work_units()
    wu = get_current_work_unit(state, wus)

    allowed, reason = evaluate(tool_name, args, state, wu)

    if allowed:
        print(json.dumps({"hookSpecificOutput": {"permissionDecision": "allow"}}))
    else:
        print(json.dumps({
            "hookSpecificOutput": {"permissionDecision": "deny"},
            "systemMessage": f"[DEEPSHIP Gate] {reason}\n状态: {state.get('current_state', '?')} | WU: {state.get('current_work_unit', '?')}\n推进到 EXECUTE 或检查 work_units.json",
        }))

    sys.exit(0)


if __name__ == "__main__":
    main()
