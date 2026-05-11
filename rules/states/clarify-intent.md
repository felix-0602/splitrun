# CLARIFY_INTENT 检查表

> **硬门禁：此状态下禁止调用任何实现 skill、禁止写任何代码。**
> "太简单不需要设计"是常见反模式。

## 触发条件

目标描述缺少以下任一 → 进入此状态：
- 可观测的用户行为
- 具体的用户入口（页面/命令/API）
- 量化的成功指标

## 必须完成

- [ ] 追问：谁用？真正要做什么？成功什么样？
- [ ] 提出 2-3 个方案 + 取舍 + 推荐
- [ ] 设计获批准后更新到 Prompt.md

## 工具

`Skill(brainstorming)` 辅助追问和方案生成

## 退出条件

- [ ] 目标已具体、设计已批准 → MAP_REALITY
- [ ] 目标已有可观测行为描述、无需澄清 → 标记 `CLARIFY_INTENT: skipped_with_reason` → MAP_REALITY
- [ ] 用户无法澄清且目标过于模糊 → BLOCK

`skipped_with_reason` 格式：在 RECORD 中写一行 "CLARIFY_INTENT skipped: 目标已包含 [具体入口/可观测行为/量化指标]"
