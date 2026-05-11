# PLAN_STEP 检查表

## 工作单元拆解

每个工作单元必须标注：

- **id** / **depends_on** / **scope** / **acceptance_tests** / **risk_level** / **rollback_plan**
- 按依赖排 DAG 顺序，互不依赖的标记为可并行

## 复杂度分级

| Tier | 标准 | 处理 |
|------|------|------|
| **Tier 1** | 单文件、确定性测试 | 简化流程 |
| **Tier 2** | 多文件行为变更 | 标准 TDD + code-reviewer |
| **Tier 3** | schema/auth/perf 变更 | 完整 TDD + security-reviewer + plan-validator |

## 硬门禁

- [ ] **CLARIFY_INTENT：已完成 或 已标记 `skipped_with_reason` → 允许 PLAN_STEP；否则 BLOCK**
- [ ] **MAP_REALITY 未完成 → 不允许 PLAN_STEP**
- [ ] **>2 个新文件或涉及新模块 → 必须先画模块边界图**
- [ ] **>5 文件或 schema 变更 → 强制 EnterPlanMode**

## 并行检测

- [ ] 子任务操作不同文件、不共享状态、不依赖对方输出 → 可并行（`dispatching-parallel-agents`）
- [ ] 有依赖 → 串行（`subagent-driven-development`）

## 工具

| 场景 | 工具 |
|------|------|
| 编写计划 | `Skill(writing-plans)` 或 `EnterPlanMode` |
| 架构设计 | `Agent(architect)` |
| 对抗审查 | `Agent(plan-validator)` (>5文件/schema变更) |
| CEO/Eng/Design 审查 | `Skill(plan-ceo-review/eng-review/design-review)` |
