# DEEPSHIP v2.3

> **可恢复分段自治的 AI 工程执行协议。**
>
> 不是"让模型无限自治"的 prompt。是一套执行纪律：把长任务拆成可检查的 Work Unit，用状态机约束推进，用 Intent-Aware Profiles 自适应场景，用 `.deepship/` 文件系统保存现场，用 fork 分会话并行，用 rotate 跨会话续命。

## 解决什么问题

AI 编程代理长时间工作最容易散——不是因为不会写代码：

- 做着做着忘了原计划
- 改 hook 顺手改 UI、CSS、DB，边界失控
- 子会话报告"完成了"，但没人验收它到底改了什么
- 上下文快满时直接失忆，下一轮纯靠猜
- prompt 写了一百条规则，但执行点没牙齿
- **所有场景走同一套严格状态机——部署也要 MAP_REALITY，调试也要 CLARIFY_INTENT**

DEEPSHIP 加一套工程纪律：**每一步都能恢复、能审计、能拒绝、能集成。** v2.3 引入 Intent-Aware Profiles，让规则根据用户意图自适应严格度。

## 核心概念

| 概念 | 做什么 |
|------|--------|
| **状态机** | 11 状态链路——当前在哪个阶段，只能做该阶段允许的事 |
| **Intent-Aware Profile** | 5 个 profile（development/deployment/debug/skill/learning），根据用户意图信号动态选择状态子集 |
| **Work Unit（WU）** | 一块有目标、有边界、有允许文件和验收测试的小任务 |
| **策略门禁** | 在错误状态或越界文件上直接拒绝工具调用 |
| **持久化** | `.deepship/state.json`、`work_units.json`、`log.jsonl` 保存现场，跨会话恢复 |
| **Fork** | 对已规划、文件边界清晰的任务开 worktree/子会话并行 |
| **Rotate** | 上下文快满时写 checkpoint，启动新会话无缝接上（counter ≥6 或上下文 ≤25% 时硬触发） |
| **Collector** | 回收子会话结果——检查边界、测试证据、跨 WU 冲突 |
| **Lane** | 隔离的并行工作通道——独立 worktree + 独立状态机 + 文件冲突检测 |
| **Revolution** | 用户批准的临时越界令牌——PLAN_STEP 中给指定路径写权限，不是绕过门禁 |
| **自动续推** | ADVANCE guard 检测到 pending WU 时自动写 `next_action`，READ_CONTEXT 强制执行 |

一句话：**DEEPSHIP 让"AI 说做完了"变成"系统验收通过了"。**

## Intent-Aware Profiles（v2.3 新增）

不再所有场景走同一套 11 状态链。READ_CONTEXT 阶段根据用户意图信号选择 profile：

| Profile | 状态子集 | 触发信号 |
|---------|---------|---------|
| `development`（默认） | 完整 11 状态 | 开发/实现/构建/重构 |
| `deployment` | READ_CONTEXT → EXECUTE → RECORD → ADVANCE | 部署/发布/ship/merge |
| `debug` | READ_CONTEXT → MAP_REALITY → EXECUTE → VALIDATE → RECORD → ADVANCE | 调试/fix/bug/investigate |
| `skill` | 绕过状态机，全放行 | `/skill-name` 显式调用 |
| `learning` | 绕过状态机，全放行 | 解释/讲解/review |

**安全网**：所有 profile 中安全触发词（auth/DB/API/加密/支付）仍触发 security-reviewer。Reality-First 在 debug profile 中不可跳过。

详细定义见 `rules/profiles.md`，profile-aware 转移逻辑见 `protocol/state-machine.md`。

## 执行流程

```
用户任务
  │
  ▼
READ_CONTEXT ──→ 读项目文件 + .deepship 状态 + 选择 Profile
  │
  ├─ profile=deployment ──→ EXECUTE（直通）
  ├─ profile=skill/learning ──→ 全放行（绕过状态机）
  │
  ▼ （默认 development 路径）
CLARIFY_INTENT (optional)
  │
  ▼
MAP_REALITY ──→ 勘察代码库现状（Reality-First）
  │
  ▼
SELECT_MILESTONE → PLAN_STEP ──→ 拆分 Work Unit，标记 execution_mode + continuation_mode
  │
  ├── execution_mode=inline ──→ 主线程执行
  ├── execution_mode=serial ──→ 单工作流执行
  └── execution_mode=fork   ──→ Dispatcher 创建 worktree，并行分派
  │
  ▼
EXECUTE ──→ 只改 files_allowed 内的文件（越界 → 走 scope 扩展流程回 PLAN_STEP）
  │
  ├── continuation_mode=rotatable + 安全点 → 写 continuation.md → Rotate → 新会话接管
  │
  ▼
VALIDATE ──→ 全局测试 / 类型检查 / 构建
  │ 失败 → REPAIR（≤3轮）→ 回 VALIDATE
  │ 计划错 → 回 PLAN_STEP
  │
  ▼
RECORD ──→ 写入 state.json + work_units.json + log.jsonl
  │
  ▼
ADVANCE ──→ 检查 pending WU
  │  有 pending + continuation_mode=normal → 自动设 next_action=continue_next_wu → READ_CONTEXT
  │  有 pending + continuation_mode=await_user → 暂停等用户确认
  │  全部 integrated + 有 pending milestone → SELECT_MILESTONE
  │  全部 integrated + 无 pending milestone → COMPLETE
```

关键区分——两轴模型：

- `execution_mode` 管执行拓扑：`inline`、`serial`、`fork`
- `continuation_mode` 管上下文续命：`normal`、`rotatable`、`await_user`

`rotatable` 不是第四种执行模式。串行 WU 可以在主工作流中 rotate，fork 出的 worker 也可以在自己的 worktree 里 rotate。

## Work Unit 示例

```json
{
  "id": "WU-004",
  "goal": "实现 useClassroom hook",
  "scope": "编排 planner、session、AI、DB 持久化。不改 UI。",
  "files_allowed": [
    "frontend/src/hooks/useClassroom.ts",
    "frontend/src/hooks/useClassroom.test.ts"
  ],
  "execution_mode": "serial",
  "continuation_mode": "normal",
  "acceptance_tests": [
    "useClassroom.test.ts 通过",
    "frontend tsc 通过"
  ],
  "depends_on": ["WU-003"],
  "status": "pending"
}
```

`files_allowed` 是纪律边界。执行中发现预估错了，走 scope 扩展流程回 `PLAN_STEP` 扩边界或拆新 WU——不应该偷偷越界（`rules/states/execute.md` §Scope 扩展有完整流程）。

## 仓库结构

```
DEEPSHIP/
├── core/manifest.md              # CC 常驻入口（~50行）——状态机骨架 + 规则加载触发器
├── rules/
│   ├── profiles.md               # Intent-Aware Profile 定义（5 profile）
│   ├── states/                   # 11 状态 JIT 检查表（每文件 30-70 行）
│   │   ├── read-context.md       #   + profile 选择 + lane 发现 + 自动续推
│   │   ├── clarify-intent.md, map-reality.md, plan-step.md
│   │   ├── execute.md            #   + scope 扩展流程
│   │   ├── validate.md, record.md, advance.md, repair.md
│   │   ├── block.md, complete.md
│   ├── static/                   # 稳定规则（受益 prompt caching）
│   │   ├── loop.md               #   自治循环纪律（rotate counter ≥6 + 自动续推）
│   │   ├── fork.md, rotate.md    #   并行 + 旋转规则
│   │   ├── code-style.md, safety.md
│   │   ├── interrupt.md, revolution.md
│   ├── intents/                  # 规则意图文档（hook deny 消息溯源）
│   │   ├── policy-code-write.md, policy-exec-gate.md
│   │   ├── policy-state-write.md, policy-wu-boundary.md
│   │   ├── coordination-session-owner.md, coordination-lane-contract.md
│   │   ├── coordination-wu-integrity.md, transition-legal.md
│   └── protocols/                # WU、日志、lane 协调协议
│       ├── work-unit.md, log-format.md, lane-coordination.md
├── protocol/                     # 权威协议层——runtime 实现必须遵守
│   ├── state-machine.md          #   状态机 + profile-aware 转移
│   ├── policy.md                 #   策略门禁 + profile 权限覆盖
│   ├── work-unit.md, persistence.md, conformance.md
│   ├── interrupt.md, revolution.md
├── schemas/                      # JSON Schema（state, work_unit, log, policy_case 等）
├── adapters/
│   ├── cc/                       # Claude Code adapter（hook 门禁 + transition CLI）
│   │   ├── hooks/deepship_gate.py    # PreToolUse hook（profile-aware + lane 冲突检测）
│   │   ├── transition_state.py       # 状态转移 CLI（profile-aware + 自动续推）
│   │   └── statusline.py
│   ├── parallel/                 # Fork / Collector / Rotate / Spawn
│   │   ├── dispatcher.py         #   fork WU → worktree + 子会话
│   │   ├── collector.py          #   回收 result.json → 边界/测试/冲突检查
│   │   ├── rotate.py             #   上下文旋转——checkpoint + 新终端
│   │   └── spawn_lane.py         #   即时 lane 创建——worktree + 交互式 CC 会话
│   ├── interrupt/                # A2A 中断——多会话协调
│   ├── revolution/               # 革命令牌——用户批准的临时越界
│   ├── session/                  # 会话仲裁——所有权 + 重复检测
│   ├── lane/                     # Lane 管理（lane.py create/finalize）
│   ├── claude-code/              # CC adapter 文档
│   └── mate/                     # Mate runtime 参考方向
├── checks/
│   ├── verify.py                 # 框架自检（L1 结构 + L2 契约）
│   └── gap_scan.py               # 设计-实现差距扫描器（L3）
├── tests/
│   ├── conformance/              # 策略/转移/WU/持久化/rotate 标准测试集
│   └── test_interrupt_*.py, test_revolution_*.py, test_lane.py, ...
├── implement/                    # 完整参考手册（归档，启动时不加载）
├── demos/                        # 示例项目
├── Prompt.md                     # 项目目标与约束（模板）
├── Plan.md                       # Milestone 切片（模板）
├── Documentation.md              # 工程持续状态——进度/决策/狗粮/已知问题
├── CHANGELOG.md, RELEASE.md
└── init_deepship.py              # 项目初始化脚本
```

## 快速检查

```bash
# 框架自检（L1 结构 + L2 契约）
python checks/verify.py

# 设计-实现差距扫描（L3）
python checks/gap_scan.py

# 全量 conformance 测试
python -m unittest discover -s tests/conformance -p "test_*.py" -v

# 模块测试
python -m pytest tests/ -v
```

## Claude Code 中的用法

DEEPSHIP 在 Claude Code 中通过三层生效：

1. **Prompt 层**：`core/manifest.md` 常驻系统提示词——提醒模型按状态机推进，进入状态时 JIT 加载 `rules/states/*.md`
2. **Hook 层**：`adapters/cc/hooks/deepship_gate.py` PreToolUse hook——profile 感知、文件越界拒绝、lane 冲突检测、旋转门禁
3. **CLI 层**：`adapters/cc/transition_state.py`——profile-aware 状态转移、ADVANCE 自动续推、guard 条件检查

Claude Code adapter 不是完整 runtime——它可以拦截很多越界行为，但真正不可绕过的硬执行层应该由 Mate 这类 runtime 在 `ToolRegistry.execute()` 层实现。详见 `protocol/policy.md` 架构诚实声明。

## Lane 并行工作

Lane 是隔离的并行工作通道，与 dispatcher 互补：

- **dispatcher**：批量分派预定义 WU（`claude -p` 非交互）
- **spawn_lane**：即时创建交互式 lane（"想到就开"）

```bash
# 创建 lane（自动创建 worktree + 启动 CC）
python adapters/parallel/spawn_lane.py --task "重构 gate hook" --files rules/states/execute.md

# 或使用 lane 管理工具
python adapters/lane/lane.py create my-lane
python adapters/lane/lane.py finalize my-lane --apply
```

**文件冲突检测**：gate hook 在 EXECUTE 中检查 `.deepship/lanes/index.json`，拒绝写入已被其他活跃 lane claim 的文件。详见 `rules/protocols/lane-coordination.md`。

## 当前状态

DEEPSHIP v2.3（Intent-Aware Profiles + lane 基础设施）：

- ✅ 状态机 + Work Unit + 持久化 + 策略门禁
- ✅ **Intent-Aware Profiles**：5 profile，自适应状态严格度
- ✅ **自动续推**：ADVANCE guard 检测 pending WU 后自动推进，block 纪律级别
- ✅ Claude Code hook——profile-aware + lane 冲突检测 + revolution 令牌
- ✅ Fork/Join——dispatcher + collector（worktree 隔离）
- ✅ Rotate——checkpoint + 新终端启动 + 硬门禁（counter ≥6）
- ✅ Lane——spawn_lane + 文件冲突检测 + 身份自动发现
- ✅ Revolution——用户批准的临时越界令牌
- ✅ A2A 中断——多会话协调（classifier + router + reconciler）
- ✅ 质保——verify.py (L1+L2) + gap_scan.py (L3) + conformance 测试套件
- ✅ 规则意图系统——hook deny 消息可溯源到具体 rule-id
- 🚧 全自动上下文旋转（检测压力 → 自动 checkpoint → 杀旧 → 新会话接管）
- 🚧 Mate runtime 的硬门禁仍是长期方向

## License

MIT
