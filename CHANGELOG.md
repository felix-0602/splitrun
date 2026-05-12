# Changelog

## [0.1.0-rc.1] — 2026-05-12

### 架构

- **JIT 规则加载架构 v2.1**：Prompt 单体静态 → 按状态动态组装。`core/manifest.md`（~50 行常驻）+ `rules/states/`（11 状态检查表，每表 30-50 行）+ `rules/static/`（稳定规则，受益 prompt caching）。`implement/` 保留为归档参考。
- **状态机单源化**：`protocol/state-machine.md` D.1 为权威源，`checks/verify.py` 双向检查。

### 执行模型

- **两轴执行模型**：`execution_mode`（inline / serial / fork）管执行拓扑；`continuation_mode`（normal / rotatable）管上下文续命。两轴正交，PLAN_STEP 显式标记。
- **Work Unit 协议**：WU 生命周期 `pending → in_progress → done → integrated`。`files_allowed` 边界约束。`depends_on` DAG 依赖。`parallel_group` fork 组名。
- **持久化状态**：`.deepship/state.json` + `work_units.json` + `log.jsonl` 实现跨会话恢复。

### 分会话并行（Fork/Join）

- **dispatcher.py**：固定 runner，读 `work_units.json`，为 `execution_mode=fork` 的 WU 组创建独立 git worktree（`../.deepship-worktrees/WU-XXX/`），启动 Windows Terminal 标签页并行执行。
- **collector.py**：回收各 worker 的 `result.json`，验证边界（changed_files ⊆ files_allowed）、测试覆盖、跨 WU 冲突。`--apply` 将 worktree 变更以 patch 方式合入主仓库。
- **安全门禁**：`--cleanup` 必须配合 `--apply`（或 `--force`），防止未合并就清理导致改动丢失。

### 会话旋转（Rotate）

- **rotate.py**：在安全点保存 checkpoint（`continuation.md`），启动新终端继续。三道硬门禁：`continuation_mode != rotatable` 拒绝、`execution_mode == inline` 拒绝、`diff_intent` 或 `next_steps` 为空拒绝。

### 协议层

- `protocol/`：状态机、work unit、策略、持久化、一致性协议。
- `schemas/`：work_unit.schema.json（含 two-axis 字段）、JSON Schema 验证。
- `tests/conformance/`：policy_cases.json、transition_cases.json、work_unit_cases.json、persistence_cases.json。
- `checks/verify.py`：框架自验证，覆盖协议完整性、schema 一致性、conformance 可执行性。

### Adapter

- **Claude Code adapter**：`adapters/cc/hooks/deepship_gate.py` PreToolUse hook，状态感知的工具门禁。
- **Mate adapter**：参考 runtime（完整硬门禁），`adapters/mate/README.md`。

---

## [v2.1] — 2026-05-11

- JIT 规则加载架构：`core/manifest.md` 从 146 行瘦身到 ~50 行
- 状态机单源化：D.1 为权威源
- verify.py 工具可用性检查 + 规则弹性分级
- 文档漂移修复

## [v2.0] — 2026-05-10

- Superpowers 融合：brainstorming、TDD 内循环、SDD、两级审查
- Ralph RFC pipeline 模式融入
- 模块深度自检（B.8）+ 接口优先设计规则
- Heartbeat + Mode Word + Help Gradient 自然沟通系统

## [v1.4] — 2026-05-08

- 契约同步 + 项目隔离 + 自验证
- checks/ 样例 + 完整生命周期规范
- ECC skill 生态裁剪：309→59 DAILY
- 工具可用性分级（必装/推荐/可选）

## [v1.3] — 2026-05-07

- 工作区感知门禁
- DeepMemories 实验（后移除，YAGNI）

## [v1.2] — 2026-05-06

- Superpowers 融入 + 突触 Skill 适配体系
- 初始 DEEPSHIP 状态机
