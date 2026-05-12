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
DOC_PATHS = ["Documentation.md", "CHANGELOG.md", "README.md", ".deepship/", "decisions/", "approvals/"]


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


def evaluate(tool_name: str, args: dict, state: dict, wu: dict | None) -> tuple[bool, str]:
    """DEEPSHIP 策略评估（与 PolicyEngine 逻辑一致）"""
    current_state = state.get("current_state", "READ_CONTEXT")
    tool_key = tool_name.lower()

    # Gate 0: COMPLETE 终态
    if current_state == "COMPLETE":
        return False, "COMPLETE 是终态，不允许工具调用"

    # Gate 1: 只读放行
    if tool_key in READONLY_TOOLS:
        return True, "只读工具不受门禁"

    # Gate 2: 状态转移
    if tool_key in TRANSITION_TOOLS:
        target = args.get("target", "")
        if target == "COMPLETE" and current_state not in ("ADVANCE", "RECORD"):
            return False, f"不能从 {current_state} 直接到 COMPLETE"
        if target == "ADVANCE" and current_state != "RECORD":
            return False, f"不能从 {current_state} 直接到 ADVANCE"
        validation_status = args.get("validation_status") or state.get("validation_status")
        if target in ("ADVANCE", "COMPLETE") and validation_status != "passed":
            return False, f"验证未通过，不能进入 {target}"
        return True, "允许转移"

    # Gate 3: Mutating 状态门禁
    if tool_key in MUTATING_TOOLS:
        if current_state == "RECORD":
            fp = args.get("file_path", "")
            if any(pattern.strip('/') in fp for pattern in DOC_PATHS) or fp.endswith('.md'):
                return True, f"RECORD 阶段允许写文档: {fp}"
            return False, f"RECORD 阶段不能改代码: {fp}"

        if current_state == "VALIDATE":
            if tool_key == "bash":
                return True, "VALIDATE 阶段允许执行验证命令"
            return False, "VALIDATE 阶段不能改代码，失败请进 REPAIR"

        if current_state in EXECUTE_STATES:
            # WU 边界
            if wu and tool_key in ("edit", "write", "multiedit", "edit_file", "write_file"):
                fp = args.get("file_path", "")
                workspace = state.get("workspace")
                if not path_in_workspace(fp, workspace):
                    return False, f"文件 {fp} 不在 workspace {workspace} 内"
                allowed = wu.get("files_allowed", [])
                if allowed and fp:
                    matched = any(
                        fp == a or fp.startswith(a.rstrip('/*') + '/')
                        for a in allowed
                    )
                    if not matched:
                        return False, f"文件 {fp} 不在当前 Work Unit files_allowed 中"
            return True, f"{current_state} 允许 {tool_name}"

        return False, f"当前状态 {current_state} 不允许 {tool_name}。需先推进到 EXECUTE"

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
