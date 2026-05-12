# DEEPSHIP 状态机协议

> **权威协议层。** 实现 DEEPSHIP 的 runtime 必须遵守此状态机定义。
> 模型可读版本见 `rules/states/`。

## 状态定义

| 状态 | 职责 | 允许操作 |
|------|------|---------|
| `READ_CONTEXT` | 读协议、项目文档、持久化状态，确定当前位置 | 只读、搜索、git status |
| `CLARIFY_INTENT` | 澄清模糊目标，提出方案 | 只读、提问、写计划文档（非代码） |
| `MAP_REALITY` | 勘察代码库，确认入口/链路/契约 | 只读、搜索 |
| `SELECT_MILESTONE` | 选择下一个可执行的 milestone | 只读、写 `.deepship/work_units.json`（仅创建结构） |
| `PLAN_STEP` | 拆解 milestone 为 work units | 写 `work_units.json`、计划文档；**禁改项目代码** |
| `EXECUTE` | 执行 work units（主线程或子代理） | 改代码（仅 `files_allowed` 内）、运行测试、更新 WU 状态为 `done` |
| `VALIDATE` | 运行验证命令，确认 AC 满足 | 测试/lint/build 命令；**禁改代码**（失败进 REPAIR） |
| `REPAIR` | 定位并修复验证失败 | 改代码、运行测试（最多连续 3 轮） |
| `RECORD` | 持久化状态、集成 WU、更新文档 | 写 `.deepship/*`、Documentation.md；**禁改项目代码** |
| `ADVANCE` | 检查 WU 状态，决定下一状态 | 只读 + transition_state |
| `BLOCK` | 记录阻塞原因，等待外部解除 | 只读、写 Documentation.md |
| `COMPLETE` | 输出交付总结，停止 | **禁改代码**；写 state.json、Documentation.md |

## 合法转移

```
READ_CONTEXT → CLARIFY_INTENT | MAP_REALITY
CLARIFY_INTENT → MAP_REALITY | BLOCK
MAP_REALITY → SELECT_MILESTONE | BLOCK
SELECT_MILESTONE → PLAN_STEP | BLOCK
PLAN_STEP → EXECUTE
EXECUTE → VALIDATE
VALIDATE → RECORD | REPAIR
REPAIR → VALIDATE | BLOCK（连续3轮失败）
RECORD → ADVANCE
ADVANCE → READ_CONTEXT（有 pending WU 或 pending milestone）| COMPLETE（全部 integrated）
BLOCK → （等待外部解除后 → READ_CONTEXT）
COMPLETE → （终态，等待用户新请求 → READ_CONTEXT）
```

## Guard 条件

转移前必须满足：

| 转移 | Guard |
|------|-------|
| → EXECUTE | `current_work_unit` 非空，`files_allowed` 已定义 |
| → VALIDATE | 当前 WU 的 acceptance_tests 至少运行过一次 |
| → ADVANCE | 当前 milestone 所有 WU 状态为 `integrated` |
| → COMPLETE | 所有 milestone 完成 且 所有 WU `integrated`（或无 WU 文档任务） |
| → REPAIR | VALIDATE 失败（有失败输出为证），且连续轮数 < 3 |
| → BLOCK | 冲突无法消解 或 REPAIR 连续 3 轮失败 |
