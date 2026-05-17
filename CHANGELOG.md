# Changelog

## [v0.2.0] — 2026-05-17

### 重命名: DeepShip → SplitRun

DeepShip 暗示一个庞大的常驻框架。v0 已经是四个按需命令的轻量工具，名字应该反映本质：**拆了就跑**。

- 全线重命名：`DEEPSHIP` → `SPLITRUN`、`deepship` → `splitrun`、`/deepship-*` → `/splitrun-*`、`.deepship/` → `.splitrun/`
- Skills: `splitrun-scope`, `splitrun-spawn`, `splitrun-status`, `splitrun-land`
- Skill 描述加入中文场景触发词

## [v0.1.1] — 2026-05-17

### 契约修复 + 硬门禁可测试化

**scope/spawn 机器可读契约对齐**
- `splitrun-spawn/SKILL.md:23`：`do not spawn` → `do_not_spawn`，与 `splitrun-scope/SKILL.md:108` 的机器可读格式一致

**dispatch 降级为 plan-only**
- `adapters/brain/dispatch.py`：不再写 `lanes/index.json`（旧版缺 `worktree` 字段，制造 verify 不通过的状态）
- 改为写 `lane_plan.json`（人工参考计划）

**硬门禁从 skill 文档提取为可测试代码**
- 新增 `adapters/gates.py`：`validate_lane_index_entry`、`parse_recommendation`、`check_boundary`、`determine_land_status`、`aggregate_lane_status`
- `checks/verify.py`：scope 检查更新为当前中文模板段落 + `parse_recommendation()` 机器字段验证；新增 5f gate contract 检查

**contract tests 恢复**
- `tests/conformance/` 重建，57 个 contract test：
  - `test_lane_index_schema.py`（6）— lane index 字段契约
  - `test_boundary_check.py`（13）— `changed_files ⊆ files_claimed` 门禁
  - `test_land_gates.py`（12）— CAN LAND 判定 + 证据完整性
  - `test_scope_recommendation.py`（9）— recommendation 字段解析
  - `test_aggregation.py`（17）— index.json + report.json → lane 状态聚合 + 端到端

## [v0.1.0] — 2026-05-17

### v0: 从常驻框架到按需命令

v2/v3 是常驻系统提示词的重框架——状态机、JIT 规则加载、Intent-Aware Profiles、
hooks、revolution、interrupt、A2A、5 层适配器、20+ 目录。

v0 是四个按需调用的命令：

- `/splitrun-scope` — 任务共识对齐，判断是否值得并行
- `/splitrun-spawn` — 拆 WU，开隔离 worktree，并行启动 CC 会话
- `/splitrun-status` — 查看 Lane 状态，判定能否 land
- `/splitrun-land` — Boundary/Evidence/Integration 三类检查 + merge + 交付摘要

### 砍掉的内容

- 状态机 + JIT 规则加载（rules/states/*.md 全删）
- Intent-Aware Profiles（rules/profiles.md 删除）
- Hook 层（boundary-guard.js, coordination-guard.js, policy-gate.js 全删）
- Revolution + Interrupt + A2A 适配器（adapters/interrupt/, revolution/, session/, lane/, cc/ 全删）
- Protocol 重文档（protocol/ 全删）
- Schemas + conformance tests（schemas/, tests/ 全删）
- implement/ 参考手册（全删）

### 保留的代码

- `adapters/brain/dispatch.py` — WU 分组逻辑
- `adapters/brain/monitor.py` — Lane 状态检查
- `adapters/parallel/spawn_lane.py` — worktree 创建 + Lane 启动
- `adapters/parallel/_utils.py` — 共享工具函数
- `checks/verify.py` — 重写为 v0 自检

---

历史版本 (v2.0 — v3.0) 见 git log。
