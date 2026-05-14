# Changelog

## [v2.3] — 2026-05-14

### Intent-Aware Profiles

- **5 个 profile**：`development`（完整 11 状态）、`deployment`（4 状态快速部署）、`debug`（保留 Reality-First 跳过规划）、`skill`（全放行）、`learning`（全放行）。`rules/profiles.md` 定义触发信号和行为规则。
- **Profile-aware gate**：`deepship_gate.py` evaluate() 在状态权限矩阵前先检查 active_profile，skill/learning 直接 ALLOW。
- **Profile-aware transition**：`transition_state.py` 支持 profile 覆盖转移表，deployment 允许 READ_CONTEXT→EXECUTE 直通。
- **8 个新 conformance 测试用例**覆盖所有 profile。

### Lane 基础设施

- **spawn_lane.py**：即时 lane 创建（git worktree + 独立 CC 会话 + lane_id.json 自动身份发现）。
- **lane-coordination.md**：lane 间文件冲突检测协议——gate hook 在 EXECUTE 中拒绝写入已被其他活跃 lane claim 的文件。
- **Revolution 令牌**：用户批准的临时越界——PLAN_STEP 中为指定路径开写权限。

### 自动续推（Auto-Continuation）

- ADVANCE guard 检测到 pending WU 时自动写入 `next_action` 到 state.json。
- READ_CONTEXT 检查 next_action：`continue_next_wu` 强制执行（block 纪律级别），`await_user` 暂停，`blocked_on_deps` 处理依赖。
- `continuation_mode` 新增 `await_user` 选项。

### 质保工具

- **gap_scan.py**：L3 设计-实现差距扫描器——从设计文档提取可验证 claims，在代码中搜索实现证据，生成 gap_report.md。
- **verify.py** 增强：更完整的自检覆盖。

### 狗粮修复

- EXECUTE 中 files_allowed 死锁 → scope 扩展流程写入 `execute.md` 和 `Documentation.md` §11。
- rotate counter 2→6（减少不必要的强制旋转）。
- execute.md 172→110 行（fork/rotate 提取到 rules/static/）。

## [v2.2] — 2026-05-13

### Integration Hardening

- **interrupt + revolution + lane + session 四模块集成**：115 个未跟踪测试全部通过，纳入 159 全量回归。
- **Hook 分层**：801 行单文件 → 4 模块（policy-gate 183 + boundary-guard 151 + coordination-guard 253 + main 187）。
- **Rotate v0.2**：`--kill-old` 平台检测杀旧终端 + `--auto-recover` 自动恢复 + cross-milestone counter 重置。
- **PLAN_STEP 死锁修复**：`--clear-rotation` 接受 PLAN_STEP。
- **规则意图系统**：hook deny 消息附加 rule-id + intent 文档（`rules/intents/` 7 文件）。
- 修复 R001-R005。

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
