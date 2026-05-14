#!/usr/bin/env python3
"""
DEEPSHIP Claude Code Adapter — PreToolUse Gate Hook（参考实现，非权威源）

权威 hook 实现为 ~/.claude/hooks/deepship-policy-guard.js（Node.js）。
本文件提供等价的 Python 参考实现，供测试和文档使用。

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
import fnmatch
from pathlib import Path


# ── 策略常量（与 tests/conformance/policy_cases.json 对齐） ──

MUTATING_TOOLS = {"edit", "write", "bash", "multiedit", "write_file", "edit_file"}
READONLY_TOOLS = {"read", "grep", "glob", "task", "skill", "read_file"}
TRANSITION_TOOLS = {"transitionstate", "transition_state"}

EXECUTE_STATES = {"EXECUTE", "REPAIR"}
ACTIVE_LANE_STATUSES = {"active", "pending", "executing", "in_progress"}

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


def find_deepship_root(workspace: str | None = None) -> Path | None:
    candidates = []
    if workspace:
        candidates.append(Path(workspace))
    candidates.extend([Path.cwd(), *Path.cwd().parents])
    for root_candidate in candidates:
        if (root_candidate / ".deepship").exists():
            return root_candidate
    return None


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


def _normalize_claim_path(path: str, root: Path | None) -> str:
    raw = str(path).replace("\\", "/").strip()
    if not raw:
        return ""
    if root:
        try:
            p = Path(path)
            if p.is_absolute():
                return p.resolve().relative_to(root.resolve()).as_posix()
        except (OSError, ValueError):
            pass
    return raw.lstrip("./")


def _claim_matches(pattern: str, target: str) -> bool:
    pattern = pattern.replace("\\", "/").rstrip("/")
    target = target.replace("\\", "/").rstrip("/")
    if not pattern or not target:
        return False
    if any(ch in pattern for ch in "*?[]"):
        return fnmatch.fnmatch(target, pattern)
    return target == pattern or target.startswith(pattern + "/")


def _path_in_list(file_path: str, allowed_paths: list[str], root: Path | None) -> bool:
    target = _normalize_claim_path(file_path, root)
    return any(_claim_matches(_normalize_claim_path(path, root), target) for path in allowed_paths)


def _revolution_allows(file_path: str, state: dict, wu: dict | None) -> bool:
    token = {}
    if wu and isinstance(wu.get("revolution"), dict):
        token = wu["revolution"]
    elif isinstance(state.get("revolution"), dict):
        token = state["revolution"]
    if token.get("status") != "approved":
        return False
    allowed_paths = token.get("allowed_paths", [])
    if not isinstance(allowed_paths, list):
        return False
    root = find_deepship_root(state.get("workspace"))
    return _path_in_list(file_path, allowed_paths, root)


def _active_lane_file_conflict(file_path: str, state: dict) -> str | None:
    root = find_deepship_root(state.get("workspace"))
    if root is None:
        return None
    index_path = root / ".deepship" / "lanes" / "index.json"
    if not index_path.exists():
        return None
    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    current_lane_id = state.get("lane_id")
    target = _normalize_claim_path(file_path, root)
    for lane_id, info in index.items():
        if lane_id == current_lane_id:
            continue
        if info.get("status") not in ACTIVE_LANE_STATUSES:
            continue
        for claimed in info.get("files_claimed", []):
            claimed_path = _normalize_claim_path(claimed, root)
            if _claim_matches(claimed_path, target):
                return lane_id
    return None


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
    """DEEPSHIP 策略评估（写分类 + 阶段门禁 + profile 感知）。"""
    current_state = state.get("current_state", "READ_CONTEXT")
    active_profile = state.get("active_profile", "development")
    tool_key = tool_name.lower()

    # Gate -1: Profile 覆盖 —— skill/learning 全放行（安全触发词除外）
    if active_profile in ("skill", "learning"):
        return True, f"profile={active_profile} — 所有工具放行"

    # Gate -0.5: deployment/debug profile 允许跳过状态的转移
    if active_profile == "deployment" and tool_key in TRANSITION_TOOLS:
        target = args.get("target") or args.get("to") or ""
        if current_state == "READ_CONTEXT" and target == "EXECUTE":
            return True, f"profile=deployment — READ_CONTEXT → EXECUTE 直通"
    if active_profile == "debug" and tool_key in TRANSITION_TOOLS:
        target = args.get("target") or args.get("to") or ""
        if current_state == "READ_CONTEXT" and target == "MAP_REALITY":
            return True, f"profile=debug — READ_CONTEXT → MAP_REALITY 直通"

    # Gate 0: COMPLETE 终态
    if current_state == "COMPLETE":
        return False, "COMPLETE 是终态，不允许工具调用"

    # Gate 1: 只读放行
    if tool_key in READONLY_TOOLS:
        return True, "只读工具不受门禁"

    # Gate 2: 状态转移 —— 校验合法转移（第一道防线）
    if tool_key in TRANSITION_TOOLS:
        target = args.get("target") or args.get("to") or ""
        if not target:
            return False, "transition_state 缺少 target/to 参数"

        # 合法转移表（与 protocol/state-machine.md 对齐）
        legal_transitions = {
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

        # Profile 覆盖：扩展合法转移表
        if active_profile == "deployment":
            legal_transitions["READ_CONTEXT"] = {"EXECUTE"}
        elif active_profile == "debug":
            legal_transitions["READ_CONTEXT"] = {"MAP_REALITY"}
            legal_transitions["MAP_REALITY"] = {"EXECUTE", "BLOCK"}

        allowed_targets = legal_transitions.get(current_state, set())
        if target not in allowed_targets:
            legal = ", ".join(sorted(allowed_targets)) if allowed_targets else "（终态）"
            return False, f"非法转移: {current_state} → {target}。合法目标: {legal}"
        return True, f"转移 {current_state} → {target} 合法"

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

        if current_state == "PLAN_STEP" and _revolution_allows(fp, state, wu):
            return True, f"PLAN_STEP revolution approved path: {fp}"

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
                conflict_lane = _active_lane_file_conflict(fp, state)
                if conflict_lane:
                    return False, f"文件 {fp} 已被活跃 lane {conflict_lane} claim"
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
