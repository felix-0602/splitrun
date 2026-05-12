# DEEPSHIP for Mate

> **Mate 是 DEEPSHIP 协议的参考 runtime 实现。**
> 目标：通过全部 4 级一致性测试（Policy + Transition + Work Unit + Persistence）。

## 架构要求

Mate 必须实现：

| 组件 | 职责 | DEEPSHIP 协议参考 |
|------|------|-------------------|
| `StateStore` | `.deepship/*` 唯一读写入口，schema 验证 | `protocol/persistence.md`, `schemas/` |
| `Policy.evaluate()` | 决定 tool/action 的 ALLOW/BLOCK | `protocol/policy.md` |
| `ToolRegistry.execute()` | mutating tool 执行前强制过 Policy | `protocol/policy.md` |
| `AuditLog` | 记录每次工具调用和状态转换 | `protocol/persistence.md` §log.jsonl |
| `transition_state()` | 受控状态转移，含 guard 检查 | `protocol/state-machine.md` |

## 一致性验收

Mate 必须通过以下全部 cases：

```
tests/conformance/policy_cases.json      → Level 1 (Policy)
tests/conformance/transition_cases.json  → Level 2 (Transition)
tests/conformance/work_unit_cases.json   → Level 3 (Work Unit)
tests/conformance/persistence_cases.json → Level 4 (Persistence)
```

## 最小硬门禁（v0.1）

1. 未 READ_CONTEXT → 拒绝 mutating tools
2. 未 PLAN_STEP → 拒绝改项目代码
3. EXECUTE 只能改 `current_work_unit.files_allowed` 内文件
4. 未 VALIDATE → 拒绝 ADVANCE/COMPLETE

## 不受 DEEPSHIP 约束的部分

- 模型选择（Mate 可用任何 LLM）
- 对话管理
- 用户界面
- 工具实现细节（只要遵守 ALLOW/BLOCK 协议）
