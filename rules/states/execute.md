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

### Fork 执行（强制纪律）

存在 `execution_mode=fork` 且 `parallel_group` 非空的 WU 组时，**EXECUTE 必须走 dispatcher，不得主线程直接执行这些 WU**。

**fork 前硬门槛**（任一不满足 → 不能 fork）：
- [ ] 同组 WU ≥ 2，全部 `status: pending`
- [ ] `depends_on` 已全部满足
- [ ] `files_allowed` 互不重叠
- [ ] 工作区干净或可安全创建 worktree

```bash
# 分派：创建 worktree + 启动终端 + 监控
python adapters/parallel/dispatcher.py --mode auto

# 回收：验证所有 worker 的 result.json
python adapters/parallel/collector.py
python adapters/parallel/collector.py --apply --cleanup
```

**fork 后强制 collector**（不能跳过）：
- [ ] 每个 fork WU 必须有 `result.json`
- [ ] collector 验证：边界 + 测试覆盖 + 格式 + 跨 WU 冲突
- [ ] 通过后 `--apply` 合并变更
- [ ] 全局 VALIDATE 通过后才能进入 RECORD
- [ ] `transition_state.py --to VALIDATE` 会检查 fork WU 是否有 result.json（无 → 拒绝）

**失败路径**：
- worker result `done + valid` → collector apply → VALIDATE
- worker result `failed` 或 invalid → REPAIR 或 PLAN_STEP
- 跨 WU 冲突 → PLAN_STEP 重新拆解

### 自旋转（rotate 纪律）

`continuation_mode=rotatable` 的 WU，**在触发条件满足时必须 rotate，不得硬撑到上下文溢出**。

**触发条件**（满足任一 → 必须旋转）：
- [ ] 当前 WU `continuation_mode=rotatable`，且子阶段完成（改动已提交/diff 可解释、测试已跑）
- [ ] VALIDATE 完成，验收测试结果已记录
- [ ] RECORD 集成完成，WU 已标记 `integrated`
- [ ] BLOCK 状态，阻塞原因已写入 Documentation.md
- [ ] 上下文明显接近耗尽（模型自觉判断 token 余量不足）

**旋转命令**：
```bash
python adapters/parallel/rotate.py \
  --diff-intent "<当前 diff 意图>" \
  --next-steps "<新会话下一步>"

# 只保存不启动终端
python adapters/parallel/rotate.py --no-spawn \
  --diff-intent "<意图>" --next-steps "<步骤>"
```

**旋转后恢复流程**：
- [ ] rotate.py 写入 `continuation.md` + 标记 `state.json._rotation_pending = true`
- [ ] 新会话 READ_CONTEXT **必须**读取 `continuation.md`
- [ ] 确认后清除 `_rotation_pending`
- [ ] 清除前 `transition_state.py --to EXECUTE` 被拒绝
- [ ] 旧会话可以关闭

**禁止旋转**：
- `execution_mode=inline`（inline 不旋转）
- 有未保存 diff 且意图未写入 continuation.md
- 测试跑到一半、结果未记录

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

## 退出条件

- [ ] 当前 work unit 改动完成且关键路径测试通过
- [ ] code-reviewer 已调（A.5.1：不跳）
- [ ] 多任务场景下审查门全部通过
- [ ] work_units.json 中当前 WU 状态已更新
