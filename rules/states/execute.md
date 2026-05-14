# EXECUTE 检查表

## 进入前必读

- [ ] `rules/static/code-style.md` — 不可变性、命名、文件/函数上限
- [ ] `rules/static/safety.md` — 安全自检清单
- [ ] `.deepship/work_units.json` — 确定当前执行的 work unit 及其边界

## Work Unit 执行

**每个 work unit 是 bounded execution unit。** 协议见 `rules/protocols/work-unit.md`。

### 主线程执行（owner = orchestrator）
- [ ] 小任务、Tier 1、需要全局判断的集成任务
- [ ] 严格遵守 `files_allowed` 边界
- [ ] 完成后更新 `.deepship/work_units.json` 中该 WU 状态为 `done`

### 子代理分派（owner = subagent:<name>）
- [ ] 大任务、Tier 2/3、互不依赖的并行任务
- [ ] 由当前 Claude Code 会话自主分派；不得依赖外部调度器作为主路径
- [ ] 分派时明确传递：goal / scope / files_allowed / acceptance_tests
- [ ] 子代理约束：
  - 只能修改 `files_allowed` 中列出的文件
  - 不允许扩大 scope
  - 完成后必须返回：changed_files / tests_run / result / risks / integration_notes
  - 不得修改 `.deepship/state.json` / `.deepship/work_units.json` / `.deepship/log.jsonl`
  - 不负责全局验证

### 子代理回收（EXECUTE 内完成，RECORD 只记录集成）
- [ ] 检查 changed_files 是否在 `files_allowed` 内 → 越界 = 回退，记录违规
- [ ] 运行该 WU 的 acceptance_tests；失败则进入 REPAIR 或标记 WU `failed`
- [ ] 主线程确认结果后，才可更新该 WU 状态为 `done`
- [ ] 子代理 done ≠ milestone done——主线程负责集成和全局 VALIDATE

### RECORD 前置要求
- [ ] 所有已完成子代理结果均已回收
- [ ] 每个 `done` WU 都有 changed_files / tests_run / risks 证据
- [ ] 未回收的子代理不得被视为完成；保留 `in_progress` 或转 `blocked`

## TDD 内循环（每个函数/模块）

```
写失败测试（RED） → 最小实现（GREEN） → 重构（IMPROVE）
```

- [ ] 先写测试：成功路径 + ≥2 条失败路径
- [ ] 最小实现：只写让测试通过的代码
- [ ] 重构：测试绿了再优化内部结构

## 模块深度自检（B.8 — 写新模块前）

- [ ] 接口能让测试覆盖所有关键行为吗？
- [ ] 测试 mock 超过 2 个吗？→ 回退重新设计
- [ ] 测一个行为穿过 3+ 个模块吗？→ 合并模块
- [ ] 引入的接缝有 ≥2 个适配器吗？→ 一个就别建
- [ ] 旧测试删了吗？→ 合并后旧测试必须删除

## 安全自检 → 见 `rules/static/safety.md` C.1 完整清单

进入 EXECUTE 时已加载 static/safety.md，不再重复列出。核心要点：
- [ ] 输入/文件/DB/API/敏感数据 → 全过一遍 C.1
- [ ] 契约同步 ≠ 扩 Diff → 见 C.2.1
- [ ] **本轮调了 code-reviewer 吗？→ 必调，不跳**

## 执行模式选择

> 工具按可用性分级：`[必装]` 框架依赖 · `[推荐]` 有则用 · `[可选]` 按需安装

| 场景 | 工具 | 可用性 |
|------|------|--------|
| 单文件简单改动 | 直接写 | — |
| 多任务串行（有依赖） | `Skill(subagent-driven-development)` | [必装] |
| 多任务并行（同会话） | `Skill(dispatching-parallel-agents)` | [必装] |
| **多任务并行（分会话）** | `python adapters/parallel/dispatcher.py --mode auto` | [推荐] |
| 通用 TDD | `Agent(tdd-guide)` | [推荐] |
| 代码审查 | `Agent(code-reviewer)` | [必装] **必调，不跳** |
| 安全审查 | `Agent(security-reviewer)` | [必装] 触发词命中时必调 |
| 语言专精 | 见 `implement/tools.md` A.3.2 语言→Agent 映射 | [可选] |

### Fork 执行 → 见 `rules/static/fork.md`

有 `execution_mode=fork` 的 WU 时加载该文件。核心：fork 前硬门槛 → dispatcher 分派 → collector 强制回收 → VALIDATE。

### 自旋转 → 见 `rules/static/rotate.md`

有 `continuation_mode=rotatable` 的 WU 时加载该文件。核心：硬门禁（counter + context）→ rotate 命令 → 新会话 --auto-recover 恢复。

## 影响面预警（D.6.4）

改以下类型前，一句话说明影响范围：
- [ ] 全局组件 / 共享路由 / 公共 API client
- [ ] 数据库 schema / 数据迁移
- [ ] 后端核心服务 / 系统提示词
- [ ] 跨模块重构（>3 文件且不属同一 feature）

## 禁止事项

- [ ] 不凭记忆写 `old_string` → Edit 前必 Read
- [ ] 不改 bug 时顺手"优化"旁边代码
- [ ] 不加"以后可能用"的抽象
- [ ] 不用空 `except:` / `catch {}`
- [ ] 子代理不得超出 `files_allowed` 范围
- [ ] **需要改 files_allowed 外的文件？→ 走完整循环，不要绕过门禁**（见下方）

## Scope 扩展：EXECUTE 中需要改 WU 范围外的文件

**这是正常路径，不是异常。** 不要用 Bash heredoc / python -c / 直接 Edit state.json 绕过。

1. 确认当前 WU 实际进度
2. 给当前 WU 加 `review_status: "skipped"` + `review_evidence: "scope extension"`
3. 走 `VALIDATE → RECORD → ADVANCE → READ_CONTEXT`
4. 新循环中 `PLAN_STEP` 创建 WU，`files_allowed` 包含你需要的所有文件
5. 回到 `EXECUTE` 继续

**反例**：用 Bash heredoc 绕过 Write hook 写代码文件
**后果**：WU 边界形同虚设 → diff 范围失控 → 无法回答"这个改动属于哪个 WU"

## 退出条件

- [ ] 当前 work unit 改动完成且关键路径测试通过
- [ ] code-reviewer 已调（A.5.1：不跳）
- [ ] 多任务场景下审查门全部通过
- [ ] work_units.json 中当前 WU 状态已更新
