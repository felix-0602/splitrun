# Documentation.md — 工程持续状态记录

> **用途**：工程的"黑匣子"——让任何人在任何时候打开都能知道到哪了、做了什么决策、怎么跑、有什么坑。
> **更新频率**：**每个 milestone 完成后**必须更新；重大决策随时追加。
> **写作者**：AI 自治维护；人复盘时审阅。
> **每个项目一份**：新项目拷贝到 `<项目>/.claude/DEEPSHIP/Documentation.md`。本全局文件同时记录 DEEPSHIP 框架自身的演进（§2/§4/§7）。

---

## 1. 当前进度

| 字段 | 值 |
|------|-----|
| 当前 Milestone | [当前 milestone 名称] |
| 状态 | [pending / in_progress / done] |
| 整体完成率 | [大概百分比或描述] |
| 上次更新 | [YYYY-MM-DD HH:mm] |
| 框架版本 | [如 DEEPSHIP v1.2] |

---

## 2. 最近决策

> 记录每个重要选择的 WHAT / WHY / ALTERNATIVES。格式简短，5-10 行即可。需要更完整记录的写进 `decisions/` 目录。

| 日期 | 决策 | 原因 | 替代方案 |
|------|------|------|----------|
| 2026-05-08 | 引入"模块深度"质量维度与接口优先设计规则（Implement.md B.8, Prompt.md §7） | 模块的第一性原理是可测试性：接口是测试面，浅模块集群让 bug 埋在实现细节里，接缝只在有 ≥2 个适配器时才成立。源自 Matt Pocock skills 工程实践 | 不引入：DEEPSHIP 只停留在项目管理层，不进入代码结构层 |
| 2026-05-08 | D.6/D.7 重写为 Heartbeat + Mode Word + Help Gradient 自然沟通系统；D.2 从 14 条精简为 5 个阻塞模式；Documentation §7 从 16 字段简化为 5 字段 | 原有合规检查清单式的汇报机制产生压力而非产生信任——规则变成了"向用户证明你在工作"。新系统基于自然对话节奏，heartbeat 就是进度，求助梯度在 BLOCK 之前提供了更轻量的求助方式 | 保留旧版：叠加更多汇报模板和合规字段 |
| 2026-05-10 | 将 Superpowers（obra/superpowers v5.1.0）和 Ralph（snarktank/ralph）的核心设计融入 DEEPSHIP 框架 | Superpowers 的 brainstorming、TDD 内循环、subagent-driven-development、两级审查和 Ralph 的模式沉淀机制填补了 DEEPSHIP 的关键空白：需求澄清、测试前置、并行执行、人类协作和知识固化。全部改动以融合而非替换方式完成——Superpowers 作为工具索引中的可用技能，DEEPSHIP 状态机作为执行框架 | 不融合：DEEPSHIP 和 Superpowers 各自独立使用，用户需要在两个系统间手动切换 |
| 2026-05-10 | ECC skill 生态裁剪：309→59 DAILY、250 LIBRARY；agents 69→21 DAILY、48 LIBRARY。Superpowers 重疊 skill 以 Superpowers 版本优先 | `/doctor` 报告 273 个 skill 描述被丢弃——ECC 全量安装导致上下文预算溢出。采用 agent-sort 分类：按实际使用记录（skillUsage）、语言栈匹配（Python/TS 保留，Go/Rust/Kotlin/Swift 等入 LIBRARY）、gstack 生态优先（用户主工具链）、领域专用归类（物流/金融/医疗/能源 22 个归入 LIBRARY）。突触 (architect-mentor) 保持完整不裁剪——其高质量示例和模板是教学核心，不应为省 token 降质。Superpowers 的 16 个 skill 质量高于 ECC 同名版本（人工审查 vs 全量倾泻），ECC 版本入 LIBRARY | 不裁剪：继续承受 273 描述丢弃；删除 22 个领域专用 skill（用户选择保留）；裁剪突触（用户选择保持完整） |

---

## 3. 运行方式

### 环境要求

- **语言/版本**：[Python 3.12 / Node 22 / Rust 1.85 / ...]
- **数据库**：[PostgreSQL 16 / SQLite / 不需要]
- **环境变量**：见 `.env.example`

### 启动命令

```bash
# 首次设置：按项目实际仓库和环境文件填写
[clone-or-open-command]
[copy-env-example-if-needed]

# 安装依赖：按技术栈选择
[install-command]

# 数据库初始化：无数据库则写“不需要”
[migration-or-seed-command]

# 开发运行
[dev-server-command]

# 运行测试
[test-command]

# 构建产物
[build-command]
```

### 健康检查

```bash
[health-check-command]   # 期望结果：[status/body/side effect]
# 无服务型项目则写 smoke check 或“不需要”
```

---

## 4. 文档与版本记录

> 按 Plan.md 的 milestone 更新。记录用户可见变化、API/数据契约变化、配置/部署变化、文档更新位置和版本策略。

| 字段 | 值 |
|------|-----|
| 版本策略 | [SemVer / 日期版本 / build 号 / git tag / 无版本] |
| 当前版本 | [v0.0.0 / YYYY.MM.DD / commit / N/A] |
| 版本来源 | [package.json / pyproject.toml / __version__ / git tag / release notes] |
| Changelog 位置 | [CHANGELOG.md / docs/releases / Documentation.md 本节 / N/A] |
| 文档入口 | [README.md / docs/ / admin guide / API docs] |

### 版本变更记录

| 时间 | Milestone | 版本变化 | 变更类型 | 用户可见变化 | 契约/迁移影响 | 文档更新 | 验证 |
|------|-----------|----------|----------|--------------|--------------|----------|------|
| 2026-05-08 19:00 | 框架演进 | minor | refactor | B.8 深度模块与接口设计 + 逃逸出口；D.6/D.7 重写为自然沟通系统；D.2 精简为 5 阻塞模式；Documentation §7 简化 | 无破坏性变化 | Implement.md, Prompt.md, Documentation.md | 人工 review |
| 2026-05-10 18:00 | Superpowers 融合 | minor | feature | +CLARIFY_INTENT 状态（需求澄清）；+TDD 内循环 + 并行子代理分派；Heartbeat 升级为 commit 风格实时报备；+D.6.6 交付总结；A.5 审查分 AI 自审/人类审查两层；工具索引新增 15 个 Superpowers+Ralph 技能；+§11 代码模式沉淀区 | 无破坏性变化 | Implement.md, Documentation.md | 人工 review |
| 2026-05-10 | 契约同步 + 项目隔离 + 自验证 | minor | feature | C.2.1 契约同步 ≠ 扩 Diff；Prompt §6 契约同步原则；C.1 新增契约检查+ReAct 自省（code-reviewer/verify.py）；VALIDATE 嵌入架构自省；项目实例架构（`.claude/DEEPSHIP/`）；checks/verify.py 自验证脚本 | 项目实例路径变化：`<项目>/DEEPSHIP/` → `<项目>/.claude/DEEPSHIP/` | Implement.md, Prompt.md, README.md, Documentation.md + 新增 .claude/DEEPSHIP/*, checks/verify.py | verify.py 4 检查中 3 PASS（Implement.md 918 行留 M2） |
| 2026-05-10 | 结构优化（M2） | minor | refactor | Implement.md 918行→拆为 `implement/` 目录（6 文件，最大 278 行）；移除 DeepMemories（3版本空壳）；清理 projects/ 临时目录 | 执行手册从单文件变为目录；DeepMemories 引用全部更新 | Implement.md→implement/*, Documentation.md, .gitignore, README.md, verify.py | verify.py ALL PASS |
| 2026-05-10 | Superpowers 深入融合 + Ralph 管道 | minor | feature | CLARIFY_INTENT 硬门禁（批准前禁实现）；EXECUTE SDD 两级审查门（Spec→Quality）；VALIDATE 验证铁律（IDENTIFY→RUN→READ→VERIFY→CLAIM）；D.1.1 TDD 反借口表；PLAN_STEP 工作单元 spec 模板 + 复杂度 Tier 1-3；D.1.2 合并队列规则；REPAIR 卡壳恢复协议；tools.md A.0 EXECUTE 拆三行 + SDD 描述修正 | 无破坏性变化 | implement/state-machine.md, implement/tools.md | verify.py ALL PASS |

### 文档更新规则

- 用户入口、API endpoint、请求/响应字段、配置项、部署方式、数据 schema、权限模型发生变化时，必须更新对应文档。
- 没有独立 changelog 的项目，至少在本节记录 milestone 级版本变化。
- 破坏性变化必须写清迁移步骤、回滚方式和受影响调用方。
- 只改内部实现且无用户可见变化时，版本变化可写 `none`，但必须说明原因。

---

## 5. 已知问题

> 记录暂未修复的 bug、技术债、临时 workaround。不要在代码里埋 `// TODO` 然后就忘了——写在这里。
>
> **技术债类条目必须包含**：违反的规则、不修复的原因、剩余风险、还债时机。

| ID | 类型 | 描述 | 违反规则 | 原因 | 剩余风险 | 还债计划 | 严重程度 | 发现日期 |
|----|------|------|----------|------|----------|----------|----------|----------|
| [自动编号] | bug/debt/workaround | [一句话] | [B.8 规则1/2/3 或"不适用"] | [为什么本轮不修] | [会有什么问题] | [M? / 下个 PR / 不还+理由] | [高/中/低] | [日期] |

### 技术债示例

| ID | 类型 | 描述 | 违反规则 | 原因 | 剩余风险 | 还债计划 |
|----|------|------|----------|------|----------|----------|
| K001 | debt | `PaymentService.charge()` 穿过 OrderRepo、InventoryService、StripeClient、EmailService 四个模块，测试需要 4 个 mock | B.8 规则2 | 合并需 3 天重构，M2 截止明天；已确认为已知风险 | 后续在 charge 里加逻辑（退款、分期）时可能改漏其中某个模块 | M3 启动时优先重构 |

**记录与未记录的区别**：
- **未记录**：3 周后别人（或你自己）看到这 4 个模块的测试 4 个 mock，不知道这是"当时来不及"还是"设计者觉得这样挺好"，于是继续往上堆 → 屎山
- **已记录**：一眼知道这是有意识的妥协，什么时候还、为什么没还、还之前要注意什么

---

## 6. 项目现实勘察记录

> 每次制定或大幅调整 Plan.md 前更新。目标是记录“项目现在真实长什么样”，包括既有断点，而不只是本轮改动造成的问题。

| 时间 | 目标/主题 | 用户入口 | 实际调用链路 | 当前契约 | 目标契约 | 既有断点 | 证据 | 后续处理 |
|------|-----------|----------|--------------|----------|----------|----------|------|----------|
| [YYYY-MM-DD HH:mm] | [要实现的目标] | [入口] | [entry -> client -> endpoint -> service -> render] | [当前 API/字段] | [目标 API/字段] | [断点列表] | [文件/命令] | [milestone/known issue/non-goal/BLOCK] |

### 现实勘察详情模板

```markdown
### Reality Scan: [YYYY-MM-DD HH:mm] - [主题]

- **用户入口**：
- **触发方式**：
- **当前调用链路**：
- **目标调用链路**：
- **当前 request/response 契约**：
- **目标 request/response 契约**：
- **调用方实际消费字段**：
- **后端/服务端已有能力**：
- **前端/调用方缺口**：
- **管理/运营入口缺口**：
- **既有断点**：
- **未知项与阻塞**：
- **证据位置**：
- **转化为计划**：
```

---

## 7. 最近运行记录

> 每轮结束时追加一条自然语言摘要。执行过程中的 heartbeat 本身就是实时日志，这里只需要一句话留存复盘线索。

| 时间 | Milestone | 完成了什么 | 下一步 | 需要你判断 |
|------|-----------|-----------|--------|-----------|
| 2026-05-10 19:45 | DEEPSHIP v1.2 | ECC skill 裁剪完成：skills 309→59 DAILY / 250 LIBRARY，agents 69→21 DAILY / 48 LIBRARY。Superpowers 重疊 skill 以 Superpowers 版本优先，ECC 同名版本入 LIBRARY。修复 fork bomb deny 规则解析错误。突触保持完整不裁剪 | 验证：下一会话观察 `/doctor` 的 dropped descriptions 数量 | 无 |

### 运行记录详情

```markdown
### Run: [YYYY-MM-DD HH:mm] - [M?]

- **本轮完成**：[文件/模块，做了什么]
- **验证结果**：[pass/fail + 命令]
- **剩余风险**：[有则写，无则"无"]
- **下一步**：[下一个动作]
- **需要你判断**：[有则写，无则"无"]
```

比旧版少了 12 个字段。需要详细信息时，心跳对话本身就是完整记录——不需要在这里重复抄一遍。

---

## 8. 评估结果解释

> 用于记录 evaluator、自动审查、覆盖率、质量仪表盘等信号。它们是辅助证据，不是最终验收。

| 时间 | 工具/来源 | 分数/结论 | 主要问题 | 后续动作 | 解释 |
|------|-----------|-----------|----------|----------|------|
| [YYYY-MM-DD HH:mm] | [evaluator/review/coverage/health] | [score/pass/fail] | [关键问题] | [修复/记录风险/无需动作] | [为什么这个信号可信或有什么局限] |

### 解释规则

- PASS 只表示通过该工具的 rubric，不代表生产可用。
- 分数提升必须对应真实风险下降；如果只是补形式化字段、日志或测试数量，必须说明真实价值。
- 删除断言、放宽测试、跳过业务场景会降低证据强度；必须记录为剩余风险或测试债。
- evaluator 提出的建议如果与 Prompt.md/Plan.md 冲突，以项目目标和硬约束为准，并记录取舍。

---

## 9. 审批记录

> 仅记录需要用户确认的不可逆或高风险操作；详细审批内容写入 `approvals/` 目录。

| 审批 ID | 时间 | 操作 | 风险等级 | 用户确认 | 执行结果 |
|---------|------|------|----------|----------|----------|
| [APP-001] | [YYYY-MM-DD HH:mm] | [操作描述] | [中/高/临界] | [确认内容/未确认] | [done/skipped/blocked] |

### 审批文件模板

```markdown
# Approval APP-001

- **时间**：
- **关联 Milestone**：
- **请求操作**：
- **风险说明**：
- **替代方案**：
- **用户确认原文**：
- **执行命令/动作**：
- **执行结果**：
```

---

## 10. 下一步

> AI 完成一个 milestone 后更新这里，写清楚下一个 milestone 是什么。

- [ ] [下一个 milestone 的任务概要]
- [ ] [待解决的已知问题]
- [ ] [待用户确认的事项]

---

## 11. 代码模式沉淀区

> **用途**：记录本项目反复出现的通用模式、约定和踩过的坑。每个条目不是"这次做了什么"——是"以后遇到类似场景应该怎么做"。
> **来源**：Ralph 的 progress.txt 启发——每次迭代中发现的通用知识不是一次性垃圾，是本项目最有价值的资产。
> **更新时机**：每次发现可复用的模式时追加；模式过时时标记为废弃而非删除。

### 模式格式

```markdown
### [模式名] — 发现于 [日期]

**场景**：[什么情况下会遇到]
**模式**：[怎么做——够具体到可以照做]
**反例**：[不要怎么做]
**后果**：[照做/不照做的实际后果]
**关联文件**：[典型例子 file:line]
```

### 收录标准

- **必须收录**：本项目特有的约定、非显而易见的依赖关系、踩过坑的 pattern
- **不必收录**：编程语言通用最佳实践、框架官方文档已有内容、一次性的 bug 修复
- **一个模式一个条目**：不要塞多个模式到一条

### 已有模式

_（暂无——发现第一个可复用模式后开始填充）_

---

> **AI 使用说明**：
> - 开始或重写计划前 → 更新 §6 项目现实勘察记录，并把断点转化为 Plan.md milestone/已知问题/non-goal
> - 完成一个 milestone → 更新 §1 进度 + §4 文档与版本记录 + §7 最近运行记录 + §10 下一步
> - 做一个技术决策 → 追加到 §2；需要更完整记录时写到 `decisions/` 目录
> - 发现一个 bug/坑 → 追加到 §5
> - 发现可复用的代码模式/约定/踩坑经验 → 追加到 §11（只记录通用模式，不记一次性细节）
> - 需要用户审批 → 追加到 §9；详细审批内容写到 `approvals/` 目录
> - 有 evaluator/coverage/review 等质量信号 → 追加到 §8，并解释它的局限和后续动作
> - 环境/运行方式变了 → 更新 §3
> - 不要为了"看起来很忙"而刷更新——每次更新必须有实质内容变化
