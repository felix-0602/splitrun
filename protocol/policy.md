# DEEPSHIP Policy 协议

> **权威协议层。** 定义每个状态下 tool/action 的 ALLOW/BLOCK 规则。
> Runtime 的 Policy Engine 必须实现此协议。一致性测试见 `tests/conformance/policy_cases.json`。

## 工具分类

| 类别 | 工具 | 含义 |
|------|------|------|
| `read` | read_file, grep, glob, git status/diff/log | 只读，不修改任何文件 |
| `read_exec` | bash 只读命令（git status/log/diff, ls, cat, npm/pip list, node -v 等） | 只读观察，无文件/环境副作用 |
| `state_write` | write(.deepship/*), append(.deepship/log.jsonl) | 写持久化状态文件 |
| `doc_write` | write(Plan.md), write(Documentation.md), write(*.md) | 写项目文档 |
| `code_write` | write_file, edit_file | 修改或创建项目代码文件 |
| `exec` | bash 变更命令（pytest, npm install, lint, build, rm 等） | 执行可能有文件/环境副作用的命令 |
| `skill_user` | Skill 工具（用户显式调用 /skill） | 用户主动键入的 slash command |
| `skill_auto` | Skill 工具（模型自动搜索/匹配） | 模型自发搜索匹配合适技能 |
| `transition` | transition_state | 请求状态转移 |

## 状态 → 工具权限矩阵

**MUST NOT** = Runtime 必须在 `ToolRegistry.execute()` 层面拒绝。

| 状态 | read | read_exec | skill_user | skill_auto | state_write | doc_write | code_write | exec | transition |
|------|------|-----------|------------|------------|-------------|-----------|------------|------|------------|
| `READ_CONTEXT` | ALLOW | ALLOW | ALLOW | MUST NOT | ALLOW | MUST NOT | MUST NOT | MUST NOT | ALLOW |
| `CLARIFY_INTENT` | ALLOW | ALLOW | ALLOW | ALLOW | ALLOW | ALLOW | MUST NOT | MUST NOT | ALLOW |
| `MAP_REALITY` | ALLOW | ALLOW | ALLOW | MUST NOT | MUST NOT | MUST NOT | MUST NOT | MUST NOT | ALLOW |
| `SELECT_MILESTONE` | ALLOW | ALLOW | ALLOW | MUST NOT | ALLOW（仅 WU 结构） | MUST NOT | MUST NOT | MUST NOT | ALLOW |
| `PLAN_STEP` | ALLOW | ALLOW | ALLOW | ALLOW | ALLOW | ALLOW | MUST NOT | MUST NOT | ALLOW |
| `EXECUTE` | ALLOW | ALLOW | ALLOW | ALLOW | ALLOW | ALLOW（仅集成文档） | ALLOW（仅 files_allowed） | ALLOW（测试+build） | ALLOW |
| `VALIDATE` | ALLOW | ALLOW | ALLOW | MUST NOT | MUST NOT | MUST NOT | MUST NOT | ALLOW（测试+lint+build） | ALLOW |
| `REPAIR` | ALLOW | ALLOW | ALLOW | MUST NOT | MUST NOT | MUST NOT | ALLOW | ALLOW（测试） | ALLOW |
| `RECORD` | ALLOW | ALLOW | ALLOW | MUST NOT | ALLOW | ALLOW（仅 Documentation.md） | MUST NOT | MUST NOT | ALLOW |
| `ADVANCE` | ALLOW | ALLOW | ALLOW | MUST NOT | ALLOW | ALLOW（仅交付总结） | MUST NOT | MUST NOT | ALLOW |
| `BLOCK` | ALLOW | ALLOW | ALLOW | MUST NOT | ALLOW（仅记录阻塞） | ALLOW（仅 §5/§9） | MUST NOT | MUST NOT | MUST NOT |
| `COMPLETE` | ALLOW | ALLOW | ALLOW | MUST NOT | ALLOW（仅 state.json） | ALLOW（仅 Documentation.md） | MUST NOT | MUST NOT | MUST NOT |

## EXECUTE 补充规则

在 `EXECUTE` 状态下，`code_write` 和破坏性 `exec` 的 ALLOW 必须同时满足：

1. `current_work_unit` 非空
2. `file_path` 在 `current_work_unit.files_allowed` 内
3. `file_path` 在 `workspace` 边界内（如配置了 workspace）
4. 不满足任一条件 → BLOCK

## Profile 权限覆盖规则

> 权威 profile 定义见 `rules/profiles.md`。当 `state.json` 中 `active_profile` 非空且非 `development` 时，以下规则覆盖状态→权限矩阵。

| Profile | 覆盖规则 |
|---------|---------|
| `skill` | **所有工具 ALLOW**。不检查状态门禁、WU 边界、files_allowed。安全触发词（auth/DB/API/加密/支付）仍触发 security-reviewer。 |
| `learning` | **所有工具 ALLOW**。规则同 skill。 |
| `deployment` | READ_CONTEXT → EXECUTE 直通：READ_CONTEXT 中允许 exec（deploy/build 命令）。EXECUTE/RECORD/ADVANCE 按原矩阵。跳过 MAP/PLAN/VALIDATE 对应的 code_write 限制。 |
| `debug` | READ_CONTEXT → MAP_REALITY 直通：跳过 CLARIFY/MILESTONE/PLAN 的 code_write 限制。MAP_REALITY 和 VALIDATE 的权限按原矩阵保留。 |

**实现要求**：Policy Engine 的 `evaluate()` 必须在检查状态权限矩阵**之前**先检查 `active_profile`。skill/learning profile 直接返回 ALLOW（除安全触发词外）。

## 状态边界补充规则

- `READ_CONTEXT` MAY 读取 `.deepship/*`、Prompt、Plan、Documentation，执行 `read_exec`（只读 bash：ls, git status, npm list 等），响应用户显式 `skill_user` 调用；MUST NOT 写项目代码、执行 `exec`（副作用 bash）、或 `skill_auto`（自动搜索匹配技能）
- `ADVANCE` MAY 读取状态、更新状态转移记录、决定 READ_CONTEXT / SELECT_MILESTONE / COMPLETE；MUST NOT 写项目代码
- 配置了 `workspace` 时，任何写入目标都 MUST 位于 workspace 内，即使该路径被列入 `files_allowed`

## transition_state 补充规则

- `from` 参数必须等于当前 `state`
- 目标 `to` 必须在合法转移表中
- 目标 Guard 条件必须满足
- 不满足 → BLOCK + 返回 `required_conditions` 列表

## 协议术语

本文档使用 RFC 2119 术语：
- **MUST** / **MUST NOT** = 协议要求，runtime 必须强制执行
- 区别于 `rules/states/*.md` 中的 SHOULD / checklist（给模型阅读的建议）
## Dynamic Planning Artifact Policy

The following paths are PLAN_STEP-only planning artifacts:

- `.deepship/sessions.json`
- `.deepship/plan-revisions/*.md`
- `.deepship/a2a/*.json`
- `.deepship/prompt-supplements/*.md`

They MAY be written in PLAN_STEP. They MUST NOT be written in EXECUTE, VALIDATE,
REPAIR, or ordinary lane execution. This prevents a session from silently
changing coordination contracts while code is being edited.
