# PLAN_STEP 检查表

## 产出：Work Units

PLAN_STEP 必须产出 work units，写入 `.deepship/work_units.json`。协议见 `rules/protocols/work-unit.md`。

每个 work unit 必填字段：
- **id** / **goal** / **scope** / **files_allowed** / **depends_on**
- **execution_mode** / **continuation_mode** / **parallel_group**
- **acceptance_tests** / **risk_level** / **owner** / **status**

## 两轴决策（PLAN_STEP 必做）

### 轴 1：执行拓扑（`execution_mode`）

| 值 | 触发条件 | 执行方式 |
|----|---------|---------|
| `inline` | Tier 1，单文件，确定性改动 | 主线程直接执行，不经过 dispatcher |
| `serial` | 长任务、大重构、跨 ≥5 文件 | 主线程串行。如果是长任务 → `continuation_mode: rotatable` |
| `fork` | 可并行拆解、文件边界清晰、plan 已定文件归属 | dispatcher 分会话并行。必须标记 `parallel_group` |

**fork 保守原则**：只能在 PLAN_STEP 明确标记。不能在执行中临时决定并行。适用：复杂任务初始实现、整体重构文件边界已定。

### 轴 2：上下文续命（`continuation_mode`）

| 值 | 触发条件 |
|----|---------|
| `normal` | 单会话能搞定（默认） |
| `rotatable` | 预计跨多会话，在安全点可旋转。通常搭配 `execution_mode: serial` |

两轴可组合：`fork` WU 也可以是 `rotatable`（分叉出的 worker 在自己的 worktree 里任务很长时可以自旋转）。

## 自主分派原则

- [ ] PLAN_STEP 定义 WU 边界和 owner；主路径由 CC 会话自主分派，外部调度器为辅助
- [ ] Claude Code 在 EXECUTE 中根据 `owner` / `depends_on` / `files_allowed` 自主决定主线程、串行子代理或并行子代理
- [ ] 并行分派前必须确认 `files_allowed` 两两不重叠
- [ ] 子代理提示必须包含：goal / scope / files_allowed / acceptance_tests / done 输出格式
- [ ] 子代理不得写 `.deepship/state.json` / `.deepship/work_units.json` / `.deepship/log.jsonl`

### 终端并行分派（可选）

当 milestone 有 ≥2 个互不依赖的 pending WU 时，可用固定 runner 做 worktree 隔离并行：

- [ ] PLAN_STEP 只产出 `work_units.json`，**不生成调度脚本**（runner 是固定的）
- [ ] 分派命令：`python adapters/parallel/dispatcher.py --mode auto`
- [ ] runner 自动为每个 WU 创建独立 git worktree（`../.deepship-worktrees/WU-XXX/`）
- [ ] 每个 worker 在自己的 worktree 中运行 `claude -p`，产出 `.deepship/runs/WU-XXX/result.json`
- [ ] worker 不得修改 `.deepship/state.json` / `.deepship/work_units.json` / `.deepship/log.jsonl`
- [ ] 回收验证：`python adapters/parallel/collector.py`（边界检查 + 测试覆盖 + 冲突检查）

## 复杂度分级

| Tier | 标准 | 处理 |
|------|------|------|
| **Tier 1** | 单文件、确定性测试 | 简化流程，主线程执行 |
| **Tier 2** | 多文件行为变更 | 标准 TDD + code-reviewer，可分子代理 |
| **Tier 3** | schema/auth/perf 变更 | 完整 TDD + security-reviewer + plan-validator，主线程 |

## 硬门禁

- [ ] **CLARIFY_INTENT：已完成 或 已标记 `skipped_with_reason` → 允许 PLAN_STEP；否则 BLOCK**
- [ ] **MAP_REALITY 未完成 → 不允许 PLAN_STEP**
- [ ] **>2 个新文件或涉及新模块 → 必须先画模块边界图**
- [ ] **>5 文件或 schema 变更 → 强制 EnterPlanMode**

## 工具

| 场景 | 工具 |
|------|------|
| 编写计划 | `Skill(writing-plans)` 或 `EnterPlanMode` |
| 架构设计 | `Agent(architect)` |
| 对抗审查 | `Agent(plan-validator)` |
| CEO/Eng/Design 审查 | `Skill(plan-ceo-review)` / `Skill(plan-eng-review)` / `Skill(plan-design-review)` |
| 并行分派 | `Skill(dispatching-parallel-agents)` |
| 串行推进 | `Skill(subagent-driven-development)` |
## New-Session Arbitration And Prompt Alignment

When a new conversation starts in the current project and `.deepship/sessions.json`
shows an active owner already executing the plan, PLAN_STEP MUST arbitrate before
creating a lane or starting execution.

Routes:

- `duplicate`: stop; the active owner already owns the same goal.
- `belongs_to_current_owner`: write an A2A handoff plus prompt supplement asking
  the owner to pause, read the supplement, reconcile the plan, and continue.
- `new_goal_requires_lane`: write a plan revision, A2A contract, and prompt
  supplement before creating any lane/worktree. The contract must define
  interfaces, file boundaries, validation commands, and integration owner.
- `plan_conflict`: do not create a lane; require the owner to stop and replan.

PLAN_STEP may write these dynamic planning artifacts:

- `.deepship/plan-revisions/*.md`
- `.deepship/a2a/*.json`
- `.deepship/prompt-supplements/*.md`
- `.deepship/sessions.json`

These artifacts are the authoritative prompt alignment inputs. A session must
read the latest relevant plan revision, A2A artifact, and prompt supplement
before continuing from an older plan.
