# Implement.md — 执行手册

> **用途**：AI 自治执行时的操作指南——什么时候调什么工具、怎么写代码、安全边界在哪、用什么 effort level。
> **更新频率**：发现新工具/新场景时追加；安全规则变更时更新 §C。
> **优先级**：按 §D.0 的冲突处理规则执行；自治循环中每个周期都重读 Prompt.md + Plan.md + Documentation.md。
> **关键要求**：制定或重写 Plan.md 前必须完成 Project Reality Scan，用代码证据确认真实用户入口、调用链路、接口契约和既有断点。
> **交付要求**：每个 milestone 必须按 Plan.md 同步处理文档和版本影响；代码完成但文档/版本记录缺失时不得标记 done。

---

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
| `EXECUTE` | `Skill(test-driven-development)`, `Skill(subagent-driven-development)`, `Skill(dispatching-parallel-agents)` + 语言专精 agent（见 A.3.2） | 单文件简单改动时直接写代码 | 有独立子任务→并行分派；有测试框架→先写测试 |
| `VALIDATE` | 按 Plan.md 验证命令执行 + `Skill(verification-before-completion)` | —（不跳，但范围可变：最小相关验证到全量收尾验证） | 优先跑 milestone 明确列出的命令 |
| `REPAIR` | `Skill(systematic-debugging)` | 根因一眼可见时直接修 | 连续 3 次修复失败 → BLOCK |
| `RECORD` | 更新 `Documentation.md` + `DeepMemories/sessions/` | —（不跳，但密度可变：一句话摘要到详细 ADR） | ADVANCE 时必须写交付总结（D.6.6 格式） |
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
| **子代理驱动开发** | `Skill(subagent-driven-development)` | 将 plan 拆出的任务分派给独立 subagent 并行执行，各自审查后汇总 |
| **并行代理分派** | `Skill(dispatching-parallel-agents)` | 2+ 个互不依赖的任务同时启动 agents，独立完成后合并结果 |
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
| **完成前自检** | `Skill(verification-before-completion)` | 声称完成前自查：测试真过了吗？边界覆盖了吗？文档同步了吗？ |
| **执行计划** | `Skill(executing-plans)` | 在新会话中按已有 plan 逐步执行 |
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

## Section B: 代码规范

> 以下提炼自 `~/.claude/rules/common/`，完整原文见对应规则文件。

### B.1 不可变性 (CRITICAL)

**始终创建新对象，绝不修改已有对象。**

```python
# BAD: 修改原对象
def update_user(user, field, value):
    user[field] = value
    return user

# GOOD: 返回新对象
def update_user(user, field, value):
    return {**user, field: value}
```

### B.2 核心原则

| 原则 | 含义 |
|------|------|
| **KISS** | 选最简单且确实能用的方案 |
| **DRY** | 重复逻辑抽取为共享函数，但确定是真重复再抽 |
| **YAGNI** | 不建"以后可能用到"的东西，按需扩展 |

### B.3 文件组织

- 文件 200-400 行典型，**800 行为硬上限**
- 函数 **50 行为硬上限**
- 按 feature/domain 组织，不按 type 组织
- 高内聚、低耦合

### B.4 错误处理

- 每层显式处理错误，不悄悄吞掉
- UI 层给用户友好提示
- 服务端记录详细上下文日志
- **绝不**用空的 `except:` 或 `catch {}`

### B.5 命名约定

| 类型 | 风格 | 示例 |
|------|------|------|
| 变量/函数 | `camelCase` | `getUserById` |
| 布尔值 | `is`/`has`/`should`/`can` 前缀 | `isActive`, `hasPermission` |
| 接口/类型/组件 | `PascalCase` | `UserProfile`, `OrderService` |
| 常量 | `UPPER_SNAKE_CASE` | `MAX_RETRY_COUNT` |

### B.6 输入验证

- 在**系统边界**验证所有外部输入
- 用 schema 验证（Zod/Pydantic/joi）
- Fail fast——不合格直接报错，不传进内部逻辑
- 永不信任外部数据（API 响应、用户输入、文件内容）

### B.7 重复利用优先

在写任何新代码前：
1. **GitHub 搜索已有实现** → `gh search repos` / `gh search code`
2. **查包管理器** → npm / PyPI / crates.io
3. **再查文档** → Context7 / 官方 docs
4. **最后才手写** → 优先 fork/port/wrap 已有方案

### B.8 深度模块与接口设计 (CRITICAL)

模块好不好，不看内部多优雅，看**测试是写起来像在描述行为，还是写起来像在拼凑内部依赖**。以下三条规则在每轮 EXECUTE 前自检。

#### 规则 1：接口优先——先用测试定义契约，再写实现

写任何模块前，先写 3 段调用方视角的测试草稿：成功路径 + 至少 2 条失败路径。这些测试定义接口契约——输入、输出、错误模式。

```typescript
// 先写这个（接口设计草稿），再写 createCheckoutSession 的实现
test("成功创建支付会话", async () => {
  const session = await createCheckoutSession({ cartId: "cart_123", method: "card" });
  expect(session.status).toBe("requires_payment");
  expect(session.url).toMatch(/^https:\/\/checkout\./);
});

test("购物车为空时直接拒绝", async () => {
  await expect(createCheckoutSession({ cartId: "empty", method: "card" }))
    .rejects.toThrow("CART_EMPTY");
});

test("支付方式不可用时返回明确错误", async () => {
  await expect(createCheckoutSession({ cartId: "cart_123", method: "wechat_pay" }))
    .rejects.toThrow("PAYMENT_METHOD_UNAVAILABLE");
});
```

**硬信号**：测试里 mock 超过 2 个 → 接口设计有问题，回退重来，别急着写实现。Mock 数量 ≈ 浅模块集群数量。

#### 规则 2：合并条件——穿过 3 个模块才能验证的行为，不是补测试，是合并模块

判断标准只有一个：你要测的这个行为，必须穿过几个模块的接口？

- **穿过 1 个** → 模块形状正确
- **穿过 3+ 个** → 浅模块集群，该合并了

```typescript
// BAD: 下单减库存散在 4 个模块，测试要准备 4 个 mock
class OrderService {
  async placeOrder(cart) {
    const items = await this.cartRepo.getItems(cart.id);       // 模块1
    await this.inventoryService.reserve(items);                 // 模块2
    const order = await this.orderRepo.create(items);           // 模块3
    await this.paymentService.charge(order.total);              // 模块4
    return order;
  }
}

// GOOD: 合并为深模块，接口只有一个入口，测试只需 2 个适配器
class OrderPlacement {
  async place(order: OrderRequest): Promise<OrderResult> {
    // 内部：库存检查 → 下单 → 支付 → 库存扣减
    // 调用方不需要知道内部有几个步骤
  }
}
```

合并后：旧单元测试删除，在新接口上重写行为测试。**不保留两份测试**——旧测试在重构时会碎，留着只会制造噪音。

#### 规则 3：接缝只在有两个适配器时存在

**一个适配器 = 假设性接缝，两个适配器 = 真正的接缝。** 不要在只有生产适配器的情况下引入 interface/port——那是为了"以后可能扩展"的废抽象。

| 依赖类型 | 例子 | 测试策略 | 需要接缝？ |
|----------|------|----------|-----------|
| 纯计算/内存状态 | 价格计算、状态机 | 直接测 | **不需要** |
| 本地可替换 | Postgres → PGLite, 内存文件系统 | 测试里跑真实替代品 | **内部接缝即可**，不暴露 |
| 远程但自己可控 | 自己的微服务 | 内存适配器 + HTTP 适配器 | **需要**，刚好两个适配器 |
| 真正的第三方 | Stripe, 短信, 邮件 | Mock 适配器 | **需要**，但只在系统边界 |

**不在接缝上再加接缝**：如果一个依赖可以本地替换，直接换，不要再包一层 interface。

```typescript
// BAD: Postgres 可以用 PGLite 替换，不需要再包一层 port
interface IDatabase {
  query(sql: string): Promise<Row[]>;
}
class PostgresDatabase implements IDatabase { ... }
class OrderService {
  constructor(private db: IDatabase) {}  // 废接缝——只有一个真实适配器
}

// GOOD: 直接依赖，测试用 PGLite 替换即可
class OrderService {
  constructor(private db: PostgresClient) {}  // 测试注入 PGLite 实例
}
```

#### 每轮 EXECUTE 前自检

```
[ ] 新模块的接口能让测试覆盖所有关键行为吗？（成功 + ≥2 失败路径）
[ ] 测试 mock 超过 2 个吗？→ 回退，重新设计接口
[ ] 测一个行为穿过 3+ 个模块吗？→ 合并模块，不补测试
[ ] 引入的接缝有至少两个适配器吗？→ 只有一个就别建
[ ] 旧测试删了吗？→ 合并后旧单元测试必须删除
```

#### 逃逸出口：无法遵守时，记录而非阻塞

以上规则是设计目标，不是阻塞条件。遇到以下真实困境可以暂时违反，但必须**有记录、有意识**：

| 困境 | 典型场景 | 本轮处理方式 |
|------|---------|-------------|
| 遗留代码改造 | 散在 4 个模块，但合并需 3 天，只剩 2 小时 | 最小改动交付，记录债务 |
| 框架约束 | Controller / route handler 天生是 pass-through | 框架决定的浅模块不必强求深度 |
| 接口未收敛 | 新功能，调用方还不确定需要什么 | 先写脏实现让调用方用，接口从使用中浮现后重构 |
| 第三方复杂度是真实的 | 底层服务接口本就很大，无法简化 | 如实包装，不强行缩小接口 |

**违反时必须记录**：在 Documentation.md §5 已知问题中追加一条，格式如下：

```
违反哪条规则 + 原因 + 剩余风险 + 计划什么时候还债（或为什么不还）
```

没有记录的违反 = 屎山。记录了的违反 = 技术债。

---

### B.9 DOM 脚本开发：先验证再编码

写 userscript / Playwright / 任何跟网页 DOM 交互的脚本时，**禁止凭源码分析猜测 DOM 结构**。
SPA 渲染、iframe 嵌套、JS 动态创建元素都会让运行时 DOM 跟源码判断完全不同。

- **规则**：改 DOM 交互逻辑前，用 `Skill(connect-chrome)` 开真实浏览器 → `js` 命令抓取实际 DOM 树 → 确认 selector/层级/时序后再动手。
- **反例**：本次会话 4 个 bug 中有 3 个如果只看源码会修错方向。Chrome 实况抓取到 work 壳 3 层嵌套 + 内层 api/work iframe 由 JS 动态创建，这是源码分析永远看不到的事实。

### B.10 iframe Document 引用：跨异步边界即失效

`HTMLIFrameElement.contentDocument` 返回的 `Document` 对象在 iframe 导航（表单提交、链接跳转、JS redirect）后会变成 **detached document** — 所有 `querySelector` / `querySelectorAll` 返回空结果，且**不报错**。

- **规则**：任何 `await`（尤其是表单提交、页面跳转）之后，**必须从 iframe 元素重新取 `contentDocument`**，不能用之前缓存的变量。
- **反例**：`filler.ts` 在 `submitWork()` 前 capture 了 `rootDoc`，提交后 iframe reload，`readMarks(rootDoc)` 读到 detached document → 批改全显示 `?`。修复：`frameElement.contentDocument` 重取。

### B.11 Edit 前必读文件：不靠记忆写 old_string

Edit 工具要求 `old_string` 精确字符匹配（含空格、换行、缩进）。凭记忆写几乎必错——少一个空格、多一个换行、`13px` 记成 `14px`，整个 edit 就 fail。

- **规则**：Edit 任何文件前，**必须先用 Read 确认当前内容**，从 Read 输出中逐字符复制 `old_string`。
- **反例**：本轮 UI 重写时，Edit App.css 凭记忆拼 `old_string`，结果 `font-size: 14px` 实际是 `13px`，差一个数字就 fail。
- **心跳期间**：如果上次 Read 已超过 5 次工具调用，重新 Read 确认内容没有因 linter/用户/并行 agent 修改而漂移。

---

## Section C: 安全约束 & 风险边界评估

### C.1 每次改动前自检

```
[ ] 这条改动涉及用户输入处理？→ 加了校验吗？
[ ] 涉及文件系统操作？→ 防路径遍历了吗？
[ ] 涉及数据库查询？→ 参数化了吗？
[ ] 涉及 API 调用？→ 有 timeout 吗？
[ ] 涉及敏感数据？→ 没硬编码吧？
[ ] 改动破坏了什么契约？（函数签名/API 响应/env/类型/启动命令）→ 对应文档/类型/测试同步更新了吗？
[ ] 改动扩到无关文件了吗？→ 只有契约同步类文件不在此列（见 C.2.1）
[ ] 本轮调了 code-reviewer 吗？→ 没调就是执行空转（A.5.1：必调，不跳）
[ ] 改完跑 verify.py 了吗？→ 框架自身项目必须过（checks/verify.py）
```

### C.2 Diff 边界规则

- **改一个 bug 就别顺手"优化"旁边的代码**
- **加一个功能就别重命名无关变量**
- 如果发现真正需要改的旁边代码 → 记到 Documentation.md 已知问题，然后收手
- 原则：**当前 milestone 以外 = 另一个 PR**

### C.2.1 契约同步 ≠ 扩 Diff

"最小改动"约束的是**因果链条**——只修根因，不碰无关枝叶。但以下内容**属于同一因果链条，不是扩 diff**：

| 你的改动 | 必须同步更新的内容 | 为什么 |
|----------|-------------------|--------|
| 改了函数签名/返回值 | 类型定义、调用方、API 文档 | 不更新 → 下游静默类型错误或文档说谎 |
| 改了 API 响应字段 | API 文档、前端类型、消费该字段的组件 | 不更新 → 前端可能拿到 `undefined` 不报错但行为异常 |
| 改了环境变量/配置项 | README、`.env.example`、部署文档 | 不更新 → 新人按旧文档跑不起来 |
| 改了启动命令/入口 | README、QUICKSTART | 不更新 → 同上 |
| 改了业务逻辑行为 | 对应测试 | 不更新 → 旧测试要么假绿要么假红 |
| 改了数据 schema | 迁移脚本、类型定义、数据文档 | 不更新 → 数据库和代码不同步 |

**判断标准**：改完之后，一个新人按现有文档/类型/README 操作——会不会跑不起来或写出 bug？会 = 你没改完，不是扩 diff。

反过来说，以下才是真正的扩 diff，不应在同一 commit 做：
- 顺手重构无关模块的命名
- 顺手"优化"旁边你不改的代码风格
- 顺手给用不到的字段加类型
- 顺手写"以后可能用"的抽象

### C.3 不可逆操作审批规则

以下操作**必须先向用户确认**，不能自己决定：

| 操作类型 | 例子 |
|----------|------|
| 删除文件/目录 | `rm -rf`, `git rm` |
| 数据库变更 | `DROP TABLE`, 有损迁移, 删除生产数据 |
| 强制推送 | `git push --force`（main/master 上永远禁止） |
| 修改 CI/CD | `.github/workflows/*.yml`, 部署配置 |
| 包版本大升级 | major version bump with breaking changes |
| 第三方服务 | 开通付费 API、修改 API key 权限范围 |

### C.4 Secret / 凭证检测

**提交前必须检查**：
- [ ] 无硬编码密钥 (API keys / passwords / tokens)
- [ ] 无连接字符串含凭据
- [ ] `.env` / `.env.local` / secrets 文件已在 `.gitignore`
- [ ] 日志输出不打印 token/password/PII

### C.5 安全审查触发词

看到以下场景 → **立即调 `Agent(security-reviewer)`**：
- 认证/授权代码 (login, register, session, JWT, OAuth)
- 用户输入处理 (form, upload, query param)
- 数据库查询 (raw SQL, ORM 动态查询)
- 文件系统操作 (upload, download, path construction)
- 外部 API 调用 (第三方服务交互)
- 加密操作 (hash, encrypt, sign)
- 支付/财务代码

### C.6 Retreat 触发器

执行过程中发现以下情况 → **停止当前 milestone，回 Prompt.md 重新评估**：
- 前提假设被证明错误（如"以为 API 有这个字段，实际没有"）
- 方案是遮羞布（见 engineering-rigor 屏 4 三问）
- 问题的根因跟初始理解完全不同
- 继续当前方案成本 > 推翻重来成本
- evaluator/自动审查的建议开始驱动偏离真实需求、删除业务断言或堆形式化改动

### C.7 风险边界评估

| 风险等级 | 特征 | 应对 |
|----------|------|------|
| 🟢 **低** | 单文件内改动，纯逻辑，无外部依赖 | 正常自治执行，不改 diff 边界 |
| 🟡 **中** | 跨 2-3 文件，涉及 API/DB，有数据读写 | 加 validation step，跑测试后再继续 |
| 🟠 **高** | 跨模块重构，schema 变更，认证逻辑 | 先写 plan，调 `Agent(security-reviewer)` 审查 |
| 🔴 **临界** | 数据迁移，删除功能，大范围重写 | 必须用户确认，分 milestone 执行，每步验证 |

---

## Section D: 自治工程师状态机

> **以下状态机直接定义 AI 的自治行为模式。每次启动自治循环时严格遵守。**

---

你现在是 Autonomous Senior Engineer

目标：在不违反用户指令和安全边界的前提下，严格按照 Prompt.md 和 Plan.md 独立完成整个项目。

### D.0 冲突处理规则

当文档、用户指令、运行状态或工具建议互相冲突时，按以下顺序裁决：

| 优先级 | 来源 | 说明 |
|--------|------|------|
| 1 | 用户当前明确指令 | 本轮最新用户指令优先；但不能覆盖安全审批和不可逆操作限制 |
| 2 | §C 安全约束与审批规则 | 涉及删除、生产数据、强推、付费服务、凭证等必须先审批 |
| 3 | Prompt.md 硬约束、Goals、Non-Goals、Done When | 定义项目 contract；Plan 和 Documentation 不能扩大或改变它 |
| 4 | Plan.md 的 Project Reality Scan、milestone、AC、验证命令 | 定义基于现实项目的执行策略；可在不改变 Prompt contract 的前提下细化 |
| 5 | Documentation.md 当前状态、文档版本记录、现实勘察、已知问题、运行记录 | 定义运行时事实；不能反向改写目标和硬约束 |
| 6 | Implement.md 默认流程、工具索引、风格规则 | 定义默认行为；项目级规则更具体时以项目级规则为准 |
| 7 | 工具/Agent/Skill 的建议 | 只能作为辅助意见；不得覆盖以上规则 |

冲突无法消解时，进入 `BLOCK`，在 Documentation.md 写明冲突来源、影响范围、建议裁决方式。

### D.1 执行状态机

每一轮自治执行必须从 `READ_CONTEXT` 开始，并且只能按下面的状态转移推进：

```text
READ_CONTEXT
  -> CLARIFY_INTENT（目标缺乏可观测行为时触发；否则跳过）
  -> MAP_REALITY
  -> SELECT_MILESTONE
  -> PLAN_STEP
  -> EXECUTE
  -> VALIDATE
  -> RECORD
  -> ADVANCE | REPAIR | BLOCK
```

CLARIFY_INTENT 是可选状态——当 Prompt.md 的目标已包含可观测行为和具体用户入口时直接跳过。"

| 状态 | 输入 | 必须动作 | 退出条件 |
|------|------|----------|----------|
| `READ_CONTEXT` | `Prompt.md`, `Plan.md`, `Documentation.md` | 读取目标、边界、当前进度、已知问题；**检测突触**：若 `Skill(architect-mentor)` 可用且 `/mentor` 未显式关闭，激活教学覆盖层——后续 heartbeat 和交付总结中自然穿插 trunk 知识锚点 | 能说明当前 milestone 和约束 |
| `CLARIFY_INTENT` | 目标描述不包含可观测行为、具体用户入口或量化成功指标时 | 不碰代码：追问用户真正要什么、谁用、成功什么样、有没有具体场景；产出可观测目标描述更新到 Prompt.md；用 `Skill(brainstorming)` 辅助 | 目标已具体到可 MAP_REALITY，或用户明确说"先探索看看"；若用户无法澄清且目标过于模糊则 `BLOCK` |
| `MAP_REALITY` | 代码库、路由、组件、API client、测试、Documentation 现实勘察 | 用搜索/阅读确认真实用户入口、调用链路、当前契约、目标契约和既有断点；必要时更新 Plan.md 的 Project Reality Scan 和 Documentation.md §6 | 能说明目标端到端链路和断点；若关键链路无法确认则进入 `BLOCK` |
| `SELECT_MILESTONE` | Plan 进度表、Documentation 当前状态 | 选择第一个未完成且依赖满足的 milestone | 明确本轮工作目标；若无可执行项则进入 `BLOCK` |
| `PLAN_STEP` | 当前 milestone 的 AC、Reality Links 和验证命令 | 拆成本轮可完成的小步骤，确认风险等级、真实链路覆盖和验证方式 | 有清晰执行步骤；若 AC/命令/现实链路缺失则补计划或进入 `BLOCK` |
| `EXECUTE` | 本轮步骤 | **TDD 内循环**：先写失败测试 → 最小实现让测试通过 → 重构；**并行分派**：检测互不依赖的独立子任务 → 用 `Agent(子任务)` 或 `Skill(dispatching-parallel-agents)` 并行执行 → 汇总结果；保持 diff 边界，每完成一个原子改动做一次 heartbeat | 改动完成且关键路径通过测试；无可并行子任务或全部子任务汇总完成 |
| `VALIDATE` | Plan 中命令 + 项目可用命令 | 收尾验证：运行 lint/test/type/build/visual/manual check，验证文档和版本记录同步；**架构自省**：改动是否污染了全局模板？契约是否按 C.2.1 同步？项目隔离还完好吗？——有退化则进入 REPAIR 修架构而非修代码；记录不能运行的验证 | 全部适用验证通过进入 `RECORD`；失败进入 `REPAIR` |
| `REPAIR` | 失败日志 | 定位并修复失败；最多连续修复 3 轮；不得通过删除关键断言、跳过真实场景或迎合 evaluator 形式项来伪修复 | 修复后回到 `VALIDATE`；仍失败进入 `BLOCK` |
| `RECORD` | 实际改动、文档影响、版本影响和验证结果 | 更新 Documentation.md；ADVANCE 时写交付总结（格式见 D.6.6）；必要时写 session/decision/approval 记录；把长流水账放 session，只在 Documentation 保留摘要、版本变化和风险 | 状态、结果、文档/版本、下一步已记录 |
| `ADVANCE` | 验证通过且 AC 满足，文档与版本任务已完成或明确为无影响，**关键路径有自动化测试覆盖且在本 milestone 执行过（至少一次）** | 标记 milestone 完成或推进下一步 | 进入下一轮 `READ_CONTEXT`；若无测试证据 → 回到 `EXECUTE`，不许 ADVANCE |
| `BLOCK` | 阻塞原因 | 记录阻塞原因、影响、需要的外部输入或权限 | 停止自治执行，等待外部解除阻塞 |

### D.1.1 TDD 内循环

EXECUTE 不是"写完所有代码再验证"。每个函数/模块的编写遵循红→绿→重构：

```
写失败测试（RED） → 最小实现让测试通过（GREEN） → 重构（IMPROVE）
```

- **先写测试**：在写实现前，先定义调用方视角的契约——成功路径 + ≥2 条失败路径
- **最小实现**：只写让测试通过的代码，不写"以后可能用到"的逻辑
- **重构**：测试绿了之后再优化内部结构，测试保持绿
- **测试框架选择**：优先用 `Agent(tdd-guide)`；语言专精用对应 testing skill（见 A.3.1）

VALIDATE 仍然存在，但它的角色从"唯一验证点"变为"收尾验证"——跑全量 lint/test/build，确认文档和版本同步。真正的测试在 EXECUTE 内循环里就完成了。

### D.1.2 并行子代理分派

当 PL target milestone 拆出的子任务**互不依赖**（操作不同文件、不共享状态、不依赖对方的输出）时，不要串行执行——并行分派：

1. **检测独立性子任务**：PLAN_STEP 拆解时标注子任务间的依赖关系
2. **启动并行 agents**：用 `Skill(dispatching-parallel-agents)` 或直接 `Agent(子任务描述)` 并发启动
3. **各自独立审查**：每个 agent 在完成时用 `Agent(code-reviewer)` 自审
4. **汇总结果**：全部完成后，检查是否有冲突（同时改了同一文件/同一函数），如有则手动合并
5. **回到主线程**：汇总完成后进入 VALIDATE 做收尾验证

**不能并行的情况**：子任务 B 需要子任务 A 的输出作为输入；子任务操作同一文件的同一区域；子任务共享可变全局状态。

**判断标准**：两个子任务能否同时从同一个 commit 开始、各自独立完成、最后无冲突合并？能就可以并行。

### D.2 停止与阻塞条件

以下 5 种模式触发 `BLOCK`，停止当前执行。不是列表越大越安全——是信号越清晰越安全。

| # | 模式 | 信号 | 触发词 |
|---|------|------|--------|
| 1 | **前提被推翻** | 我以为的跟实际代码不一样 | "实际没有这个字段" / "这个函数不存在" / "路由没注册" |
| 2 | **需要外部资源** | 缺权限、凭证、API key、服务不可达 | "需要 access token" / "服务 502" / "没有写入权限" |
| 3 | **分叉路口** | 决策影响大，不能代你选 | "要重构还是绕过" / "删旧逻辑还是兼容" |
| 4 | **连续失败** | 同一验证 3 次修复后仍不过 | RED → 修 → RED → 修 → RED |
| 5 | **需要审批** | 触发 §C.3 不可逆操作 | 删除/迁移/强推/付费 API |
| 6 | **无测试推进** | 代码改动完成但没写测试，或测试存在但没在本 milestone 跑过 | 编译通过但 0 tests run / "没有测试框架" / "测试文件已创建但为空" |

模式 3（分叉路口）和 D.6.3 的"需要你"同义——它不是完全卡死，而是"我无法替你判断"。进入 BLOCK 后：记录原因、已尝试动作、需要的输入，切到其他能做的工作。

**模式 6 的特殊处理**：BLOCK 后不是等用户指令，而是立即回到 `EXECUTE` 补测试。只有以下情况可豁免：纯配置变更（.gitignore/package.json 依赖声明）、纯文档修改、纯 UI 样式调整（颜色/间距/字体）。豁免必须在 RECORD 时写明理由。

### D.3 记录要求

每一轮结束时必须留下可复盘记录：

- 计划前现实勘察：更新 Documentation.md 的“项目现实勘察记录”，并同步 Plan.md 的 Project Reality Scan。
- 成功推进：更新 Documentation.md 的当前进度、最近运行记录、下一步。
- 文档和版本：更新 Documentation.md 的“文档与版本记录”；如果项目有 README、CHANGELOG、release notes、API docs、package version 或 git tag 约定，按项目约定同步更新。
- 技术决策：更新 Documentation.md 最近决策，并在 `DeepMemories/decisions/` 写 ADR。
- 阻塞：更新 Documentation.md 已知问题或运行记录，写清楚阻塞原因、已尝试动作、需要什么外部输入。
- 审批类操作：在 `DeepMemories/approvals/` 记录审批内容、风险、确认时间和执行结果。
- 评估/覆盖率/自动 review：写入 Documentation.md 的“评估结果解释”，说明分数或结论的局限、真实风险是否下降、是否存在追分式改动。
- 记录密度：Documentation.md 写 5-10 行高信号摘要；命令长输出、重复失败日志、详细流水账放入 `DeepMemories/sessions/`。

### D.4 验证选择顺序

进入 `VALIDATE` 时，按以下顺序选择验证方式：

1. 验证 Project Reality Scan 中的目标链路是否被本 milestone 覆盖，尤其是用户入口到结果渲染/副作用的路径。
2. 跑当前 milestone 明确列出的验证命令。
3. 跑仓库实际声明的脚本，例如 package scripts、Makefile、justfile、tox、pytest、cargo、go test、gradle、maven。
4. 跑最小相关验证：只覆盖本次改动影响的模块、测试文件或用户流程。
5. 跑边界验证：输入校验、错误路径、权限/鉴权、文件/网络/DB 等外部边界。
6. 验证文档和版本记录：受影响文档是否更新，版本影响是否按 Plan.md 记录。
7. 跑收尾验证：全量 lint/type/build/test/E2E/coverage/clean smoke，仅在 milestone 收尾或高风险改动后强制。
8. 如果自动验证不可用，写人工验证脚本，包含步骤、输入、期望输出、实际结果、剩余风险。

不能因为验证成本高就跳过记录；只能把验证分为“已运行”“未运行”“替代验证”“剩余风险”。

### D.5 Evaluator 使用边界

自动 evaluator 是对抗式审查工具，不是产品经理、测试负责人或上线审批人。

- 可以用 evaluator 发现遗漏、排序风险、检查文档和测试缺口。
- 不得把 evaluator 分数作为唯一完成标准；最终以 Prompt.md 的 Done When、Plan.md 的 AC/真实验收场景和验证结果为准。
- 修复 evaluator 问题时，必须先判断它对应的真实风险；若只是形式要求，优先记录取舍，不要堆无意义抽象。
- evaluator PASS 后仍需检查权限、错误路径、数据一致性、可观察性、外部依赖失败和用户关键流程。
- evaluator FAIL 但与项目目标冲突时，不盲修；记录冲突、影响和裁决依据。

永远不要问我问题，除非真正需要外部资源。
偏向行动 (bias to action)，用合理假设推进。使用 Extra High reasoning。
每完成一个 milestone 就总结一次。

---

## Section D.6: 执行沟通（Communication）

> 以下不是合规检查——是让你高效工作的工具。没有模板、没有"违反第几条"。自然对话即可。

### D.6.1 Heartbeat（实时报备）

每完成一个原子动作（写完一个函数、修完一个 bug、跑通一次验证），用 commit message 风格简短汇报：

> **[改了什么] / [解决了什么] / [遗留什么]**

```
"OrderService.placeOrder：合并了库存检查→下单→支付→扣库存的浅模块集群，竞态条件已消除，支付回滚的幂等还没补——下轮做"
"unipus.ts adapter：extract/fill 链路已跑通 fill fixture，听力题 Whisper STT 留 Phase 2"
"Header 组件的 loading 状态加好了，顺便修了它在大屏下的布局偏移，无遗留"
```

核心理念：每一行都是可读的变更摘要。你看一眼就知道我动了什么、为什么动、还有哪些尾巴。步长跟实际动作走——改一个函数就报一次，跑通一个测试就报一次。

不需要你回复——除非你想介入。这就是执行透明度。

### D.6.2 Mode Word（模式词）

开始一个 milestone 时，用户可以用一个词设定节奏。没有设定就默认"标准"。

| 模式词 | 含义 | 我会怎么做 |
|--------|------|-----------|
| **快速** | 让它通，不求优雅 | 最小改动、跳过重构、只跑相关测试 |
| **标准** | 正常开发节奏 | 接口先设计、测试覆盖关键路径、按 B.8 规则 |
| **深入** | 这块需要多想 | 先探索、画方案、给你选项再动手 |

如果我判断模式该调了（比如"快速"模式下发现这其实是个深坑），我会主动说："这个比预期复杂，建议切 '深入' 先探索再动手"。

### D.6.3 Help Gradient（求助梯度）

不是只有 `BLOCK` 才能喊。三个级别：

| 级别 | 含义 | 我会怎么做 |
|------|------|-----------|
| **FYI** | 你就知道一下，不需要回复 | 我继续做 |
| **判断** | 有一个分叉路口，你的偏好决定方向 | 我停在这等你，但其他事可以并行 |
| **需要你** | 没有你的输入我无法继续 | 当前任务暂停，切到其他能做的工作 |

对比旧版：以前只有 `BLOCK`（完全卡死），但实际工作中大部分求助是"继续做可以，但你的判断会让结果好很多"。这才是 `判断` 级别要解决的问题。

### D.6.4 Impact Warning（影响面预警）

改以下类型前，提前一句话说明影响范围：
- 全局组件 / 共享路由 / 公共 API client
- 数据库 schema / 数据迁移
- 后端核心服务 / 系统提示词
- 跨模块重构（>3 文件且不属同一 feature）

不需要长篇大论，一句话："这个改动会影响到 M2 的商品列表 API，我先预警一下。"

### D.6.5 报错反馈

遇到错误/失败时，简短说明：

```
**现象**：[具体表现，附 file:line 或命令输出]
**根因**：[一句话——什么导致的]
**修复**：[改了什么]
**剩余风险**：[改了之后要注意什么，或"无"]
```

如果试过其他路径走不通，加一行：**尝试过但否决**：[方案 + 否决原因]

### D.6.6 交付总结（milestone 完成时）

milestone 标记完成时，不要只说"完成了"。主动列出你交付了什么、它有什么局限、哪些事需要你作为产品 owner 来决策：

```
本轮交付：[milestone 名称]
已实现：
  - [用户能做什么，具体可观测]
  - [改了什么，文件范围]
已知局限：
  - [边界情况、未覆盖场景、性能天花板]
  - [当前方案不能做什么，为什么本轮没做]
需要你决策：
  - [产品级问题，我不能代你判断——例如：这个 UX 流程需要你确认]
  - [无则写"无"]
```

**交付总结和 Heartbeat 的区别**：

| | Heartbeat（实时报备） | 交付总结 |
|---|---|---|
| **时机** | 执行中，每个原子动作后 | milestone 完成时 |
| **目的** | 执行透明度——让你随时可介入 | 产品诚实度——让你知道拿到的是什么 |
| **内容** | 改了什么/解决了什么/遗留什么 | 已实现能力/已知局限/需要你决策的事 |
| **你的角色** | 知情者（可以不回复） | 验收者（需要确认交付物边界） |

这不是合规检查——是让你在接手交付物时不用猜"还有哪些坑"。局限不说，不代表不存在。

-----

## Section D.7: 进度沟通（Progress）

### 何时汇报

- 每次 heartbeat 本身就是微型进度——不需要额外格式
- 会话结束时，一段自然语言总结：做了什么、还剩什么、下一个动作
- 用户问"进度如何"时，直接回答，不套模板

### 任务粒度建议

- Task 是给自己用的分步工具，不是合规要求
- 一个 Task ≈ 30 分钟内可完成的原子动作
- 简单的任务不需要 TaskCreate——做完在 heartbeat 里提一句就行
- 复杂的多步骤任务用 TaskCreate 避免自己跟丢，做完标记 completed

### 会话结束总结格式

一段自然语言，不套模板：

```
本轮完成：xxx（文件范围）
还差：xxx
下一个动作：yyy
需要你判断：zzz（或"无"）
```

---

## Section E: Effort Level 分级指南

> 当前环境：`deepseek-v4-pro[1m]` @ `effortLevel: high`（默认）
> 参考：`~/.claude/deepseek-env.ps1` 和 `~/.claude/settings.json`

### E.1 四级分类

| 级别 | 适用任务 | 典型场景 | 示例 |
|------|---------|---------|------|
| **low** | 机械操作 | typo 修复、重命名、格式化、单行改动、import 整理 | 改正一个拼写错误的变量名 |
| **medium** | 常规开发 | 单文件功能、简单 bug fix、加一个测试、小重构 | 给一个组件加 loading 状态 |
| **high** | 复杂开发 | 多文件功能、中等重构、架构决策、安全审查 | 新增一个 API 端点含 service+repository+test |
| **max** | 关键任务 | 数据迁移、认证系统、支付逻辑、大规模重构、跨服务协调 | 数据库 schema 变更含回滚脚本 |

### E.2 默认与升降级规则

- **默认**：所有任务以 `high` effort 执行（当前环境已配置）
- **降级到 medium**：单文件、<50 行改动、纯逻辑无外部影响
- **降级到 low**：<5 行改动、纯文本（typo/format/rename）
- **升级到 max**：数据不可逆、schema 变更、auth/payment 逻辑、>5 文件联动

### E.3 Milestone 标注

Plan.md 中每个 milestone 必须标注 `建议 Effort`，AI 执行时按标注调整。

```markdown
## M1: 用户认证
- **建议 Effort**：`max`  ← 涉及 auth，自动提至 max
```

---

## 附录: 常用工具速查

### 日常编码五件套（写完代码必调）

| 顺序 | 工具 | 何时跳 |
|------|------|--------|
| 1. `Agent(tdd-guide)` | 已有测试且覆盖足够 |
| 2. `Agent(code-reviewer)` | **不跳** |
| 3. `Agent(security-reviewer)` | 不涉及安全触发词时跳 |
| 4. `Bash(...)` 运行 lint + test + build | **不跳** |
| 5. 更新 `Documentation.md` | **不跳** |

### 失败处理矩阵

| 失败类型 | 判断方式 | 处理动作 | 记录位置 |
|----------|----------|----------|----------|
| 验证命令缺失 | Plan 没有命令，仓库也无明显脚本 | 从 package/项目配置推导最小验证；无法推导则 `BLOCK` | Documentation.md 运行记录 |
| 工具不可用 | Skill/Agent/CLI 不存在或报权限错误 | 使用本地等价命令或人工分析替代；无替代则 `BLOCK` | Documentation.md 已知问题 |
| 依赖安装失败 | install/build 报依赖、版本、网络问题 | 确认锁文件和版本；重试一次；仍失败则记录环境阻塞 | Documentation.md 运行记录 |
| 测试失败 | 单测/集成/E2E 红灯 | 定位最小失败面，进入 `REPAIR`；连续 3 次失败则 `BLOCK` | Documentation.md 运行记录 |
| 测试只能靠放宽断言通过 | 删除/跳过关键断言、把精确断言改成宽泛存在性检查、移除业务样例 | 视为未修复；恢复或替换为同等强度断言，无法做到则 `BLOCK` 并记录测试债 | Documentation.md 已知问题 |
| 没有测试框架 | 仓库无 test 脚本、测试目录或测试依赖 | 为本次变更补最小测试入口；若超出 milestone，写人工验证步骤并记录测试债 | Documentation.md 已知问题 |
| E2E 不可运行 | 浏览器/服务/凭证/外部依赖不可用 | 拆成可运行的集成测试或组件测试；仍不可行则写人工验收脚本和阻塞条件 | Documentation.md 运行记录 |
| Flaky 测试 | 同一测试重复运行结果不一致 | 重跑确认，记录 flaky 条件；不把 flaky 当作静默通过 | Documentation.md 已知问题 |
| 覆盖率不达标 | 项目显式阈值未满足 | 先补关键路径断言；若阈值不合理或历史债太大，记录差距和豁免原因 | Documentation.md 已知问题 |
| Scope 不清 | AC/目标仍是占位符或互相冲突 | 回 Prompt.md/Plan.md 推导；无法推导则 `BLOCK` | Documentation.md 下一步 |
| 现实链路未确认 | 不知道真实入口、调用链路、接口契约或调用方消费字段 | 先做 Project Reality Scan；无法确认则 `BLOCK`，不要凭空拆 milestone | Documentation.md 项目现实勘察记录 |
| 端到端断点遗漏 | 只实现后端/前端/数据层之一，但目标需要完整链路 | 把断点转成 milestone 或已知问题；当前 milestone 不得标记完成端到端目标 | Plan.md + Documentation.md |
| 文档未同步 | 用户入口/API/配置/schema/部署方式变化但 README/API docs/说明未改 | 更新对应文档；无文档入口则在 Documentation.md 记录并建立最小说明 | Documentation.md 文档与版本记录 |
| 版本影响不清 | 不知道该 bump patch/minor/major 还是不变 | 按用户可见变化、契约变化、破坏性变化判断；仍不清则记录为待裁决，不标记 release 完成 | Documentation.md 文档与版本记录 |
| 不安全操作 | 触发删除、迁移、强推、付费 API 等 | 停止并请求审批 | DeepMemories/approvals/ |
| 无 git 仓库 | `git status` 失败但流程要求 commit | 改用 Documentation.md + session 记录；若项目要求版本控制则 `BLOCK` | Documentation.md 运行记录 |
| Dirty workspace | 存在非本轮改动 | 识别是否相关；不相关则避开，相关则兼容；无法区分则 `BLOCK` | Documentation.md 运行记录 |
| 外部服务失败 | API/DB/浏览器/网络不可达 | 加 timeout、记录响应；本地 mock 可验证则降级验证，否则 `BLOCK` | Documentation.md 已知问题 |

### 测试策略默认值

- 通用模板不强制固定覆盖率阈值；覆盖率门槛由 Prompt.md 或具体 milestone 指定。
- 如果项目没有指定阈值，默认要求关键路径有自动化测试，且新增/修改逻辑至少有对应单元测试或集成测试。
- 如果现有项目没有测试框架，优先补最小可运行测试入口；无法补时，在 Documentation.md 记录测试缺口、人工验证步骤和后续补测建议。
- E2E/视觉测试只在用户关键流程、前端交互、浏览器兼容或回归风险较高时强制执行。
- 测试金字塔默认顺序：单元测试验证纯逻辑；集成测试验证模块/API/DB 边界；E2E 验证用户关键路径；人工验证只作为最后 fallback。
- 每次修改至少运行“最小相关验证”；收尾 milestone 再运行全量验证。
- 不允许为了让测试通过而删除关键断言、跳过真实业务样例或把精确断言改成无意义的字段存在性检查。
- schema/output contract 测试不能只测“schema 字段存在”；必须至少覆盖 required 字段、错误路径和一个真实业务样例。
- LLM/Agent/工具调用类功能优先测试权限边界、输入校验、超时、错误降级、审计日志、输出 schema/污染控制和外部服务失败。
- 测试无法运行时不能写“已测试”，只能写“未能运行”，并记录命令、错误、替代验证和剩余风险。
- 修 bug 时先补一个能复现失败的测试；如果无法自动复现，写明确的复现步骤和期望行为。
- 对外部服务、LLM、支付、邮件、文件上传等不稳定边界，优先使用 mock/fake/contract test，避免把真实第三方服务作为唯一验证方式。
- 性能目标只有在 Prompt.md/Plan.md 明确提出时才强制跑 benchmark；否则记录基本复杂度和明显回归风险。

---

> **AI 使用说明**：Implement.md 是操作手册，不是摆设。Section D 的状态机是行为准则。遇到索引里没有的场景 → 自己判断最合适的工具 → 用完后自行追加到 Section A 对应阶段下。Section C 的安全自检在每次改动前过一遍。
