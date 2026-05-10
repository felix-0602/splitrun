# 工具索引

> 覆盖 `~/.claude/skills/`（200+ skills）和 `~/.claude/agents/`（60+ agents）。
> **调用格式**：Skills 用 `Skill(<name>)`，Agents 用 `Agent(<agent-name>)`。
> 发现更好的调用方式或新场景 → 自行追加到对应阶段下。

## Section A: 工具索引（按开发阶段）

> 以下索引覆盖 `~/.claude/skills/`（200+ skills）和 `~/.claude/agents/`（60+ agents）。
> **调用格式**：Skills 用 `Skill(<name>)`，Agents 用 `Agent(<agent-name>)`。
> **后续开发中发现更好的调用方式或新场景 → 自行追加到对应阶段下。**

### A.0 状态→工具速查矩阵

> 每个 D.1 状态机的状态对应哪些工具。**这是建议而非铁律**——如果当前任务的实际情况跟典型场景不同，用自己的判断。此表优先级为 D.0 第 7 级（工具建议），不覆盖用户指令、安全规则或项目约束。

| 当前状态 | 首选工具 | 何时跳过 | 关键判断 |
|----------|----------|----------|----------|
| `READ_CONTEXT` | `Read(Prompt.md)`, `Read(Plan.md)`, `Read(Documentation.md)` | —（不跳） | 能说出当前 milestone 是什么、硬约束有哪些 |
| `CLARIFY_INTENT` | `Skill(brainstorming)` | 目标已有可观测行为描述时跳过整个状态 | 目标模糊→追问；目标清晰→直接进入 MAP_REALITY |
| `MAP_REALITY` | `Grep`, `Glob`, `Read`, `Agent(code-explorer)` | 小改动且入口/链路已确凿时简化为单次 Grep | 必须确认：用户入口、调用链路、既有断点 |
| `PLAN_STEP` | `Skill(writing-plans)`, `Agent(planner)`, `EnterPlanMode` | <3 文件且无架构影响时直接列步骤 | >5 文件或 schema 变更 → 强制 EnterPlanMode |
| `EXECUTE` — 单任务 | `Skill(test-driven-development)` + 语言专精 agent（见 A.3.2） | 改动 < 3 文件且逻辑简单时直接写 | 先写测试（RED）→ 最小实现（GREEN）→ 重构 |
| `EXECUTE` — 多任务串行 | `Skill(subagent-driven-development)` | 单文件简单改动时不用 SDD | 任务互不依赖但不能并行（共享状态）→ 每任务走 SDD 两级审查（Spec → Quality） |
| `EXECUTE` — 多任务并行 | `Skill(dispatching-parallel-agents)` | 任务有依赖时回退到串行 | 任务操作不同文件、无共享状态 → 同时启动多个 agent |
| `VALIDATE` | 按 Plan.md 验证命令执行 + `Skill(verification-before-completion)` | —（不跳，但范围可变：最小相关验证到全量收尾验证） | 优先跑 milestone 明确列出的命令 |
| `REPAIR` | `Skill(systematic-debugging)` | 根因一眼可见时直接修 | 连续 3 次修复失败 → BLOCK |
| `RECORD` | 更新 `Documentation.md` | —（不跳，但密度可变：一句话摘要到详细记录） | ADVANCE 时必须写交付总结（D.6.6 格式） |
| `ADVANCE` | 标记 milestone 完成 → 交付总结 → 下一轮 READ_CONTEXT | — | 确认 AC 全部满足 + 文档/版本已同步才能 ADVANCE |
| `BLOCK` | 记录阻塞原因到 Documentation.md §5 或 §9 | — | 写清楚：阻塞原因、已尝试动作、需要什么外部输入 |

**使用方式**：每个自治循环从 READ_CONTEXT 开始 → 看当前在哪个状态 → 查此表选工具 → 执行 → 推进到下一状态。工具是参考，不是枷锁。

### A.1 Research（调研阶段）

| 场景 | 工具 | 说明 |
|------|------|------|
| 快速搜代码/文件 | `Grep`, `Glob` | 直接搜索，不要用 `grep`/`find` 命令 |
| 深度探索代码库 | `Agent(Explore)` | 中等探索，"quick"/"medium"/"very thorough" |
| 追踪执行路径、映射架构 | `Agent(code-explorer)` | 深层代码分析 |
| 查库/框架最新文档 | `Skill(documentation-lookup)` | 走 Context7 MCP |
| GitHub 搜索已有实现 | `Bash(gh search repos ...)` | 找现有轮子 |
| Web 调研 | `WebSearch`, `WebFetch` | 外部信息 |
| 神经网络搜索 | `Skill(exa-search)` | Exa MCP 搜索 |
| 多源深度调研 | `Skill(deep-research)` | firecrawl + exa 多源 |
| 需求分析 | `Skill(product-lens)` | "为什么建"验证 |
| 产品规格生成 | `Skill(prp-prd)` | 交互式 PRD 生成 |

### A.2 Plan（规划阶段）

| 场景 | 工具 | 说明 |
|------|------|------|
| **需求澄清** | `Skill(brainstorming)` | 在勘察代码前先追问用户真正要做什么、谁用、成功什么样（对应 CLARIFY_INTENT 状态） |
| 项目现实勘察 | `Grep`, `Glob`, `Read`, `Agent(code-explorer)` | 计划前确认真实入口、调用链路、API 契约和既有断点 |
| 产品规格生成 | `Skill(prd)` | 将需求转化为结构化的 PRD 文档 |
| 编写执行计划 | `Skill(writing-plans)` | 从 spec/需求出发，编写清晰到初级工程师都能执行的计划 |
| 实现方案分解 | `Agent(planner)` 或 `EnterPlanMode` | 复杂功能/多文件改动用 EnterPlanMode |
| 系统架构设计 | `Agent(architect)` | 新功能/重构/架构决策 |
| 代码级架构设计 | `Agent(code-architect)` | 基于现有 codebase 模式的实现蓝图 |
| 对抗式计划审查 | `Agent(plan-validator)` | >5 文件 / >200 LOC / schema 变更 / API 契约变更 |
| CEO 视角审查 | `Skill(plan-ceo-review)` | 产品/战略方向、scope 审查 |
| 工程视角审查 | `Skill(plan-eng-review)` | 架构、数据流、测试策略 |
| 设计视角审查 | `Skill(plan-design-review)` | UI/UX 设计审查 |
| DX 审查 | `Skill(plan-devex-review)` | 开发者体验审查 |
| 全量自动审查 | `Skill(autoplan)` | CEO+Eng+Design+DX 自动流水线 |
| 代码库分析 | `Skill(gsd-map-codebase)` | 并行 mapper 产出 `.planning/codebase/` |
| 创建功能计划 | `Skill(prp-plan)` | 含 codebase 分析和模式萃取 |

### A.3 Implement（编码阶段）

#### A.3.1 TDD 工作流

| 场景 | 工具 | 说明 |
|------|------|------|
| 通用 TDD | `Agent(tdd-guide)` 或 `Skill(test-driven-development)` | 先写关键路径测试；覆盖率阈值以 Prompt.md / Plan.md 为准。tdd-guide 侧重过程引导，test-driven-development 侧重红→绿→重构纪律 |
| **TDD 反模式检查** | `Skill(test-driven-development)` 内的 testing-anti-patterns | 写测试前自查常见误区 |
| C++ 测试 | `Skill(cpp-testing)` | GoogleTest/CTest |
| Go 测试 | `Skill(golang-testing)` | table-driven + benchmarks |
| Python 测试 | `Skill(python-testing)` | pytest + fixtures |
| Rust 测试 | `Skill(rust-testing)` | unit + integration + async |
| Kotlin 测试 | `Skill(kotlin-testing)` | Kotest + MockK |
| C# 测试 | `Skill(csharp-testing)` | xUnit + FluentAssertions |
| Django 测试 | `Skill(django-tdd)` | pytest-django + factory_boy |
| Spring Boot 测试 | `Skill(springboot-tdd)` | JUnit 5 + Mockito |
| Laravel 测试 | `Skill(laravel-tdd)` | PHPUnit + Pest |

#### checks/ 临时验证脚本约定

项目 `.claude/DEEPSHIP/checks/` 目录用于存放**一次性验证脚本**：

- **用途**：项目特有的临时检查——API 响应字段验证、HTML fixture 结构确认、跨文件引用完整性检查等
- **生命周期**：写完 → 跑通 → 验证结果 → **删除**。不累积历史遗物
- **如果复用了**：说明它不该在 checks/ 里——移入项目正式测试套件
- **不可替代**：checks/ 是临时脚本区，不是测试框架的替代品。正式测试用 A.3.1 中的对应框架

与全局 `checks/verify.py` 的区别：全局的是 DEEPSHIP **框架自检**（模板污染、状态机漂移、文件大小），项目级的 checks/ 是**该项目的一次性验证脚本**。

#### A.3.2 语言专精审查 Agent

| 语言 | Reviewer Agent | Build Resolver Agent |
|------|---------------|---------------------|
| C++ | `Agent(cpp-reviewer)` | `Agent(cpp-build-resolver)` |
| Go | `Agent(go-reviewer)` | `Agent(go-build-resolver)` |
| Python | `Agent(python-reviewer)` | — |
| Rust | `Agent(rust-reviewer)` | `Agent(rust-build-resolver)` |
| TypeScript/JS | `Agent(typescript-reviewer)` | `Agent(build-error-resolver)` |
| Java/Spring Boot | `Agent(java-reviewer)` | `Agent(java-build-resolver)` |
| Kotlin | `Agent(kotlin-reviewer)` | `Agent(kotlin-build-resolver)` |
| Flutter/Dart | `Agent(flutter-reviewer)` | `Agent(dart-build-resolver)` |
| C#/.NET | `Agent(csharp-reviewer)` | — |
| SQL/DB | `Agent(database-reviewer)` | — |

#### A.3.3 框架/领域专项 Skills

| 领域 | 可用 Skills |
|------|------------|
| **前端** | `Skill(frontend-patterns)`, `Skill(frontend-design)`, `Skill(frontend-slides)`, `Skill(nextjs-turbopack)`, `Skill(nuxt4-patterns)`, `Skill(dart-flutter-patterns)`, `Skill(compose-multiplatform-patterns)`, `Skill(swiftui-patterns)` |
| **后端** | `Skill(backend-patterns)`, `Skill(api-design)`, `Skill(django-patterns)`, `Skill(springboot-patterns)`, `Skill(laravel-patterns)`, `Skill(nestjs-patterns)`, `Skill(dotnet-patterns)`, `Skill(golang-patterns)`, `Skill(kotlin-ktor-patterns)`, `Skill(rust-patterns)`, `Skill(python-patterns)`, `Skill(perl-patterns)` |
| **数据库** | `Skill(postgres-patterns)`, `Skill(clickhouse-io)`, `Skill(database-migrations)`, `Skill(jpa-patterns)`, `Skill(kotlin-exposed-patterns)` |
| **部署/DevOps** | `Skill(deployment-patterns)`, `Skill(docker-patterns)`, `Skill(setup-deploy)`, `Skill(bun-runtime)` |
| **安全** | `Skill(django-security)`, `Skill(springboot-security)`, `Skill(laravel-security)`, `Skill(perl-security)`, `Skill(healthcare-phi-compliance)`, `Skill(hipaa-compliance)`, `Skill(defi-amm-security)`, `Skill(llm-trading-agent-security)`, `Skill(evm-token-decimals)`, `Skill(nodejs-keccak256)` |
| **移动** | `Skill(android-clean-architecture)`, `Skill(swift-concurrency-6-2)`, `Skill(swift-actor-persistence)`, `Skill(swift-protocol-di-testing)` |
| **AI/ML** | `Skill(pytorch-patterns)`, `Skill(claude-api)`, `Skill(cost-aware-llm-pipeline)`, `Skill(foundation-models-on-device)` |
| **媒体** | `Skill(fal-ai-media)`, `Skill(videodb)`, `Skill(nutrient-document-processing)`, `Skill(video-editing)`, `Skill(manim-video)`, `Skill(remotion-video-creation)` |

#### A.3.4 代码辅助

| 场景 | 工具 | 说明 |
|------|------|------|
| **子代理驱动开发（SDD）** | `Skill(subagent-driven-development)` | 多任务**串行**执行：每任务 → 实现子代理 → Spec 合规审查 → Code Quality 审查 → 两个审查都 ✅ 才能下一个任务。全程不暂停问"要继续吗" |
| **并行代理分派** | `Skill(dispatching-parallel-agents)` | 2+ 个**互不依赖、操作不同文件**的任务同时启动 agents。完成汇总后检查冲突 |
| 代码简化/规范 | `Agent(code-simplifier)` | 保持行为不变 |
| 死代码清理 | `Agent(refactor-cleaner)` | knip/depcheck/ts-prune |
| 性能优化 | `Agent(performance-optimizer)` | profiling/内存/算法 |
| 可观察性 | `Agent(silent-failure-hunter)` | 静默失败/吞错误/不良 fallback |
| 类型设计审查 | `Agent(type-design-analyzer)` | 封装/不变式/有用性 |
| 注释质量分析 | `Agent(comment-analyzer)` | 准确性/完整性/腐烂风险 |
| 构建修复 | `Agent(build-error-resolver)` | 通用；C++/Go/Java/Rust/Kotlin/Dart 有各自专精 |
| 浏览器自动化 | `Skill(browse)` | 无头浏览器测试/截图 |
| 真实浏览器测试 | `Skill(connect-chrome)` | 带 Side Panel 的 Chrome |
| 代码质量仪表盘 | `Skill(health)` | 聚合 type checker/linter/test runner |

### A.4 Test（验证阶段）

| 场景 | 工具 | 说明 |
|------|------|------|
| TDD 指导 | `Agent(tdd-guide)` | 强制先测后码 |
| **系统化调试** | `Skill(systematic-debugging)` | 遇到 bug 时先定位根因再修，不靠猜（对应 REPAIR 状态） |
| **完成前自检** | `Skill(verification-before-completion)` | **铁律**：没在当前消息里跑过验证命令 = 不能声称通过。"应该能过" = 撒谎。证据先于断言 |
| **执行计划** | `Skill(executing-plans)` | 在新会话中按已有 plan 逐步执行（无 subagent 支持时用；有 subagent 优先用 SDD） |
| **分支收尾** | `Skill(finishing-a-development-branch)` | 实现完成、测试全过后，决定分支去向（合并/PR/归档） |
| E2E 测试 | `Agent(e2e-runner)` 或 `Skill(e2e-testing)` | 关键用户流 |
| PR 测试分析 | `Agent(pr-test-analyzer)` | 行为覆盖评审 |
| 浏览器 QA（交互+修复） | `Skill(qa)` | 系统性测试 + 修 bug |
| 浏览器 QA（仅报告） | `Skill(qa-only)` | 只出报告不改代码 |
| UI 视觉审计 | `Skill(design-review)` | 视觉一致性/间距/层次 |
| Django 验证 | `Skill(django-verification)` | migration + lint + tests |
| Spring Boot 验证 | `Skill(springboot-verification)` | build + analysis + tests |
| Laravel 验证 | `Skill(laravel-verification)` | env + lint + analysis + tests |
| 通用验证循环 | `Skill(verification-loop)` | 测试 + lint + type check 循环 |

### A.5 Review（审查阶段）

> 审查分两层：**AI 自审**（每次改动后立即执行，保证代码底线）和**人类审查**（milestone 完成时，让 human partner 确认交付物方向）。

#### A.5.1 AI 自审（每次改动后必调）

| 场景 | 工具 | 说明 |
|------|------|------|
| **通用代码审查** | `Agent(code-reviewer)` | 每次写完代码必调，不跳 |
| **安全审查** | `Agent(security-reviewer)` | 涉及 auth/输入/文件/支付/加密必调 |
| PR 综合审查 | `Skill(review)` | diff 审查含 SQL/LLM/SEO |
| Codex 二方意见 | `Skill(codex)` | OpenAI Codex 独立审查 |
| 圣塔式双审 | `Skill(santa-method)` | 两个独立 reviewer 对抗验证 |
| 安全扫描（Claude 配置） | `Skill(security-scan)` | `.claude/` 目录安全审计 |
| 全栈安全 | `Skill(cso)` | secrets/依赖/攻击面 |
| 代码质量仪表盘 | `Skill(health)` | 多工具聚合 |

#### A.5.2 人类审查（milestone 完成时）

AI 自审只是代码质量底线。以下场景需要 human partner 介入：

| 场景 | 工具 | 说明 |
|------|------|------|
| **请求人类审查** | `Skill(requesting-code-review)` | 准备好 diff → 向 human partner 说明改了什么/为什么这样改/有什么风险 → 等待反馈 |
| **接收审查反馈** | `Skill(receiving-code-review)` | 逐条理解反馈意图 → 判断是否真需要改 → 有疑问就回问，不无脑全改 |
| **交付总结** | 见 D.6.6 格式 | milestone 完成时主动列出已实现能力/已知局限/需要你决策的事 |

**核心原则**：AI reviewer 帮你守住代码质量底线（安全、规范、测试），但它不理解产品意图。产品方向、UX 取舍、边界决策——这些只有 human partner 能判断。不要自动采纳所有 review 建议，先理解为什么，再决定怎么改。

### A.6 Deploy（部署阶段）

| 场景 | 工具 | 说明 |
|------|------|------|
| 发布 PR + 审查 | `Skill(ship)` | merge base + tests + review + bump version |
| 合并 + 部署 + 验证 | `Skill(land-and-deploy)` | PR → CI → deploy → 产品验证 |
| 部署后监控 | `Skill(canary)` | 看 console error / perf / 异常 |
| 部署配置 | `Skill(setup-deploy)` | 自动检测部署平台 |
| 发布后文档更新 | `Skill(document-release)` | doc 跟 diff 交叉引用 |
| 配置 IDE/VSCode | `Skill(setup-gbrain)` | gbrain 初始化 |
| 版本记录/发布说明 | `Bash(git log ...)`, `Bash(git diff ...)` | 生成 changelog/release notes 的事实依据 |

### A.7 Monitor & Maintain（监控维护）

| 场景 | 工具 | 说明 |
|------|------|------|
| 性能回归检测 | `Skill(benchmark)` | baseline 对比 |
| bug 系统调查 | `Skill(investigate)` | 科学方法四阶段 |
| 周回顾 | `Skill(retro)` | 分析 commit 历史/工作模式 |
| SEO 审计 | `Skill(seo)` | 技术 SEO + on-page |
| 代码库审计 | `Skill(repo-scan)` | 跨栈源码资产分类 |
| 自动化审计 | `Skill(automation-audit-ops)` | 自动化资产盘点 |
| 知识管理 | `Skill(knowledge-ops)` | knowledge base 管理 |
| **Git Worktree 隔离** | `Skill(using-git-worktrees)` | 需要隔离工作空间时创建独立 worktree，不污染主工作区 |

### A.8 项目管理 (GSD 系统 + Ralph 自治循环)

> GSD = Get Shit Done，一个完整的项目管理系统。以下只列常用命令，完整列表见 `Skill(gsd-help)`。

| 场景 | 工具 |
|------|------|
| 新项目初始化 | `Skill(gsd-new-project)` |
| 新 milestone | `Skill(gsd-new-milestone)` |
| 讨论阶段 | `Skill(gsd-discuss-phase)` |
| 创建阶段计划 | `Skill(gsd-plan-phase)` |
| 执行阶段 | `Skill(gsd-execute-phase)` |
| 进度查看 | `Skill(gsd-progress)` |
| 暂停工作 | `Skill(gsd-pause-work)` |
| 恢复工作 | `Skill(gsd-resume-work)` |
| 创建 PR | `Skill(gsd-pr-branch)` |
| 发布 | `Skill(gsd-ship)` |
| 审计 milestone | `Skill(gsd-audit-milestone)` |
| 清理归档 | `Skill(gsd-cleanup)` |

#### Ralph 自治循环

> Ralph 是面向 PRD 驱动项目的自治代理循环。如果你有结构化的 `prd.json`，可以用它自主完成所有 user story。

| 场景 | 工具 | 说明 |
|------|------|------|
| 生成 PRD | `Skill(prd)` | 将功能需求转化为结构化 PRD |
| 转换为 Ralph 格式 | `Skill(ralph)` | 将 PRD 转为 `prd.json` 供 Ralph 循环使用 |
| 运行 Ralph 循环 | `Bash(./ralph.sh)` | 自治执行 prd.json 中所有未通过的 user story |

Ralph 的核心设计：每次迭代读 prd.json → 选最高优先级未通过 story → 实现 → 跑质量检查 → commit → 更新 prd.json → 追加 progress.txt（含学习记录和模式沉淀）。这和 DEEPSHIP 的状态机互补——DEEPSHIP 偏向探索性/架构性开发，Ralph 偏向需求明确的机械推进。

### A.9 学习 & 知识 (突触系统)

| 场景 | 工具 | 说明 |
|------|------|------|
| 开启教学 | `/mentor on` | 全程激活 CS 教学覆盖层 |
| 关闭教学 | `/mentor off` | |
| 状态查看 | `/mentor status` | |
| 深度讲解 | `/mentor deep <主题>` | |
| 学科诊断 | `/mentor diagnose <学科>` | |
| 艾宾浩斯复习 | `/mentor review` | |
| 整体复盘 | `/mentor recap` | 工作 walkthrough |
| 功能地图 | `/mentor map` | |
| 提取可复用模式 | `Skill(learn)` | |

---
