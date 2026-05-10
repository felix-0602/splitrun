# Implement — 执行手册

> AI 自治执行时的操作指南。本目录按职责拆分了原 Implement.md。

## 文件导航

| 你需要... | 文件 | 内容 |
|-----------|------|------|
| 查当前状态该用什么工具 | `tools.md` | A. 工具索引（状态→工具矩阵 + 按阶段索引） |
| 了解怎么写代码 | `code-style.md` | B. 代码规范（不可变性、命名、模块设计、DOM 脚本） |
| 改动前做安全自检 | `safety.md` | C. 安全约束 + E. Effort Level |
| 理解状态机怎么运转 | `state-machine.md` | D. 状态机 + 沟通（Heartbeat、Help Gradient、交付总结） |
| 常用速查 | `appendix.md` | 五件套、失败处理矩阵、测试策略、checks 临时脚本约定 |

## 优先级

文件间内容冲突时，按 `state-machine.md` D.0 的冲突处理规则裁决。

## 变更规则

- 新增工具/技能 → 追加到 `tools.md` 对应阶段
- 新增代码规则 → 追加到 `code-style.md`
- 安全规则变更 → 更新 `safety.md`
- 状态机/沟通规则变更 → 更新 `state-machine.md`
