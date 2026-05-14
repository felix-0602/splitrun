# DEEPSHIP

> **可恢复分段自治的 AI 工程执行协议。**
> DEEPSHIP 是协议规范层，不是 runtime。协议文档在 `protocol/`，可验证 schema 在 `schemas/`，一致性测试在 `tests/conformance/`。
> Runtime 实现（Mate、Claude Code adapter）通过一致性测试证明兼容。

## 入口

**每次收到 Small+ 请求，进入 READ_CONTEXT，必须读取：**

| 必须读取 | 文件 |
|----------|------|
| 当前状态 | `.deepship/state.json` |
| 项目目标 | `Prompt.md` |
| 项目计划 | `Plan.md` |
| 项目记录 | `Documentation.md` |
| JIT 检查表 | `rules/states/` 对应状态文件 |
| Intent-Aware Profile | `rules/profiles.md` |
| 自治约束 | `rules/static/loop.md` |

## 状态机（详见 `protocol/state-machine.md`）

```
READ_CONTEXT → CLARIFY_INTENT(opt) → MAP_REALITY → SELECT_MILESTONE
  → PLAN_STEP → EXECUTE → VALIDATE → RECORD → ADVANCE
                                            ↓
                              有 pending WU → READ_CONTEXT
                              无 pending WU → COMPLETE

失败 → REPAIR（≤3轮）→ VALIDATE | BLOCK
```

**模型每轮是 bounded execution unit。通过 `.deepship/` 持久化实现跨会话恢复。不承诺无限自治。**

## 架构诚实声明

DEEPSHIP 的三层影响力（prompt + hook + cron）是影响力机制，不是机械保证。真正的硬门禁需要 runtime 层 ToolRegistry 拦截（见 `protocol/policy.md`）。在 Claude Code 中，DEEPSHIP 通过 manifest + `.deepship/` + hook 提升约束——但 CC 工具执行权仍在模型/runtime 手里。完整硬执行见 `adapters/mate/`。

## 自验证

`python checks/verify.py`
