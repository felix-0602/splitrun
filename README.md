# DEEPSHIP — 现实优先的自洽开发框架（v2.1）

> AI 自治开发的执行框架——不是项目管理工具，是"AI 怎么干活"的行为规范。
> 架构：**JIT 动态规则加载**（基于大模型五层工业化架构）。

## JIT 架构

```
系统提示词常驻 → core/manifest.md（<70 行，状态机骨架 + 规则加载触发器）
  ↓ 状态转换时按需 Read
rules/states/<state>.md（检查表，21-65 行）
  ↓ EXECUTE 额外加载
rules/static/{code-style,safety}.md（稳定规则，受益 prompt caching）
  ↓ 详细查询
implement/（完整参考手册，不自动加载）
```

## 文件体系

| 目录/文件 | 职责 | 加载方式 |
|-----------|------|---------|
| `core/manifest.md` | 状态机骨架 + 规则加载触发器 + 硬约束 | **常驻**（系统提示词） |
| `rules/states/` | 10 个状态检查表，每状态进入时 Read | **JIT 按需** |
| `rules/static/` | 代码规范 + 安全约束（稳定，可缓存） | **EXECUTE 时加载** |
| `Prompt.md` | 项目目标、硬约束、非目标、Done When | **项目模板**（READ_CONTEXT 时加载） |
| `Plan.md` | Milestone 切片、Reality Scan、AC、验证命令 | **项目模板**（READ_CONTEXT 时加载） |
| `Documentation.md` | 活文档：进度、决策、已知问题、运行记录 | **项目实例**（READ_CONTEXT 时加载） |
| `implement/` | 完整执行手册（工具索引、状态机原文、附录） | **归档参考**（不自动加载） |

## 核心流程

> 权威源：`core/manifest.md`。`implement/state-machine.md` 为完整原文归档。

```
READ_CONTEXT
  → CLARIFY_INTENT（目标缺乏可观测行为时触发，否则跳过）
  → MAP_REALITY → SELECT_MILESTONE → PLAN_STEP
  → EXECUTE（含 TDD 内循环 + SDD 两级审查 + 并行分派）
  → VALIDATE → RECORD → ADVANCE | REPAIR | BLOCK
```

**每次进入新状态必须先 `Read rules/states/<state>.md`。这是硬门禁，不可跳过。**

## 关键原则（按 effort tier 分级执行）

| 原则 | Trivial | Small | Medium+ |
|------|---------|-------|---------|
| **Reality-First**：先搜代码确认入口/链路/契约 | 跳过 | 简化 | **必执行** |
| **TDD**：先写失败测试 → 最小实现 → 重构 | 跳过 | 补关键断言 | **完整红→绿→重构** |
| **安全自检**（C.1） | 跳过 | 自检 | **必过清单** |
| **code-reviewer** | 跳过 | 跳过 | **必调** |
| **交付总结**（D.6.6） | 跳过 | 一行 heartbeat | **完整格式** |

豁免必须在 RECORD 时写明原因。连续跳过 = 空转信号。

## 项目结构

DEEPSHIP 分两层：**全局框架**（一份）+ **项目实例**（每个项目一份）。

```
~/.claude/DEEPSHIP/                    ← 全局框架
  core/manifest.md                     ← JIT 入口（唯一常驻）
  rules/                               ← JIT 规则
    states/                            ← 10 个状态检查表
    static/                            ← 稳定规则（受益缓存）
  implement/                           ← 完整参考手册（归档）
    tools.md / code-style.md / safety.md / state-machine.md / appendix.md
  Prompt.md / Plan.md / Documentation.md  ← 通用模板
  checks/verify.py                     ← 框架自验证脚本
  README.md                            ← 本文件

<项目>/.claude/DEEPSHIP/               ← 每个项目的真相源
  Prompt.md                            ← 项目目标、硬约束、Done When
  Plan.md                              ← Milestone、AC、Reality Scan
  Documentation.md                     ← 项目进度、决策、已知问题
  checks/                              ← 项目临时验证脚本
```

**新项目初始化**：`mkdir -p .claude/DEEPSHIP/{checks,approvals,decisions}`，从全局拷贝三个模板。

**自验证**：`python checks/verify.py`

## 版本管理

- 按 Plan.md 中 milestone 的版本变化记录
- `Documentation.md` §4 记录每次变更类型和影响

## 与 Claude Code Harness 的双向关系

DEEPSHIP 是**全局开发框架**（唯一真相源），Claude Code 的以下组件**索引或派生**自 DEEPSHIP：

| 组件 | 关系 | 维护规则 |
|------|------|----------|
| `~/.claude/CLAUDE.md` | **索引指针** → DEEPSHIP | DEEPSHIP 目录结构变化时同步更新 |
| `~/.claude/rules/common/*.md` | **派生规则** ← DEEPSHIP §B/C | DEEPSHIP 的代码规范/安全约束变更时须同步 |
| `~/.claude/settings.json` | 独立配置 | DEEPSHIP 推荐 tool/skill，配置属 harness 层 |

**修改 DEEPSHIP 时的检查清单：**
- [ ] 如果改了代码规范：同步 `rules/static/code-style.md` → `rules/common/coding-style.md`
- [ ] 如果改了安全约束：同步 `rules/static/safety.md` → `rules/common/security.md`
- [ ] 如果改了状态机/流程：同步 `core/manifest.md` → `CLAUDE.md` 索引
- [ ] 如果文件结构变了：更新 `README.md` + `CLAUDE.md` + `implement/index.md`
- [ ] 改完跑 `python checks/verify.py`

## 许可

MIT
