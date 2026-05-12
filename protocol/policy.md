# DEEPSHIP Policy 协议

> **权威协议层。** 定义每个状态下 tool/action 的 ALLOW/BLOCK 规则。
> Runtime 的 Policy Engine 必须实现此协议。一致性测试见 `tests/conformance/policy_cases.json`。

## 工具分类

| 类别 | 工具 | 含义 |
|------|------|------|
| `read` | read_file, grep, glob, git status/diff/log | 只读，不修改任何文件 |
| `state_write` | write(.deepship/*), append(.deepship/log.jsonl) | 写持久化状态文件 |
| `doc_write` | write(Plan.md), write(Documentation.md), write(*.md) | 写项目文档 |
| `code_write` | write_file, edit_file | 修改或创建项目代码文件 |
| `exec` | bash（含 pytest, npm, lint 等） | 执行命令 |
| `transition` | transition_state | 请求状态转移 |

## 状态 → 工具权限矩阵

**MUST NOT** = Runtime 必须在 `ToolRegistry.execute()` 层面拒绝。

| 状态 | read | state_write | doc_write | code_write | exec | transition |
|------|------|-------------|-----------|------------|------|------------|
| `READ_CONTEXT` | ALLOW | ALLOW | MUST NOT | MUST NOT | MUST NOT（除 git status） | ALLOW |
| `CLARIFY_INTENT` | ALLOW | ALLOW | ALLOW | MUST NOT | MUST NOT | ALLOW |
| `MAP_REALITY` | ALLOW | MUST NOT | MUST NOT | MUST NOT | MUST NOT（除安全探测） | ALLOW |
| `SELECT_MILESTONE` | ALLOW | ALLOW（仅 WU 结构） | MUST NOT | MUST NOT | MUST NOT | ALLOW |
| `PLAN_STEP` | ALLOW | ALLOW | ALLOW | MUST NOT | MUST NOT | ALLOW |
| `EXECUTE` | ALLOW | ALLOW | ALLOW（仅集成文档） | ALLOW（仅 files_allowed） | ALLOW（测试+build） | ALLOW |
| `VALIDATE` | ALLOW | MUST NOT | MUST NOT | MUST NOT | ALLOW（测试+lint+build） | ALLOW |
| `REPAIR` | ALLOW | MUST NOT | MUST NOT | ALLOW | ALLOW（测试） | ALLOW |
| `RECORD` | ALLOW | ALLOW | ALLOW（仅 Documentation.md） | MUST NOT | MUST NOT | ALLOW |
| `ADVANCE` | ALLOW | ALLOW | ALLOW（仅交付总结） | MUST NOT | MUST NOT | ALLOW |
| `BLOCK` | ALLOW | ALLOW（仅记录阻塞） | ALLOW（仅 §5/§9） | MUST NOT | MUST NOT | MUST NOT |
| `COMPLETE` | ALLOW | ALLOW（仅 state.json） | ALLOW（仅 Documentation.md） | MUST NOT | MUST NOT | MUST NOT |

## EXECUTE 补充规则

在 `EXECUTE` 状态下，`code_write` 和破坏性 `exec` 的 ALLOW 必须同时满足：

1. `current_work_unit` 非空
2. `file_path` 在 `current_work_unit.files_allowed` 内
3. `file_path` 在 `workspace` 边界内（如配置了 workspace）
4. 不满足任一条件 → BLOCK

## 状态边界补充规则

- `READ_CONTEXT` MAY 读取 `.deepship/*`、Prompt、Plan、Documentation；MUST NOT 写项目代码
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
