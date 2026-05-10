# DEEPSHIP — 现实优先的自洽开发框架（v1.4）

> AI 自治开发的执行框架——不是项目管理工具，是"AI 怎么干活"的行为规范。每个项目独立一份 `.claude/DEEPSHIP/`。

## 四文件体系

| 文件 | 职责 | 何时读写 |
|------|------|----------|
| `Prompt.md` | 项目目标、硬约束、非目标、Done When | 项目开始写定，scope 变更时更新 |
| `Plan.md` | Milestone 切片、Reality Scan、AC、验证命令 | 计划前做 Reality Scan，完成后标记 |
| `Documentation.md` | 活文档：进度、决策、已知问题、运行记录 | 每 milestone 完成后必须更新 |
| `implement/` | 执行手册：工具索引、代码规范、安全约束、状态机 | 发现新工具/场景时追加 |

## 核心流程

```
READ_CONTEXT
  → CLARIFY_INTENT（目标模糊时触发，否则跳过）
  → MAP_REALITY → SELECT_MILESTONE → PLAN_STEP
  → EXECUTE（含 TDD 内循环 + 并行子代理分派）
  → VALIDATE → RECORD → ADVANCE | REPAIR | BLOCK
```

## 关键原则

- **Reality-First**：制定计划前必须用代码搜索确认真实入口、调用链路、契约和既有断点
- **需求硬门禁**：设计批准前禁止写代码。2-3 个方案 + 取舍 + 推荐，批准后才实现
- **契约同步**：改函数签名/API/env/类型/启动命令时，文档和测试是同一改动的组成部分
- **模块深度**：接口即测试面；mock 超过 2 个说明模块太浅；一个适配器的接缝是废抽象
- **TDD 铁律**：生产代码 → 测试存在且先失败过。没有"太简单不用测"
- **SDD 两级审查**：多任务串行时每任务必经 Spec 合规 → Code Quality 审查，都 ✅ 才下一个
- **验证铁律**：没在当前消息里跑过验证命令 = 不能声称通过。证据先于断言
- **交付总结**：milestone 完成时主动列出已实现/已知局限/需要你决策

## 项目结构

DEEPSHIP 分两层：**全局框架**（一份）+ **项目实例**（每个项目一份）。

```
~/.claude/DEEPSHIP/                    ← 全局框架（模板 + 执行手册）
  Prompt.md                            ← 通用模板
  Plan.md                              ← 通用模板
  Documentation.md                     ← 通用模板（含框架自身演进记录）
  implement/                           ← 执行手册（全局共享）
    ├── index.md
    ├── tools.md / code-style.md / safety.md / state-machine.md / appendix.md
  README.md                            ← 本文件
  checks/verify.py                     ← 自验证脚本

<项目>/.claude/DEEPSHIP/               ← 每个项目自己的真相源
  Prompt.md                            ← 项目目标、硬约束、Done When
  Plan.md                              ← Milestone、AC、Reality Scan
  Documentation.md                     ← 项目进度、决策、已知问题
```

**新项目初始化**：在项目根目录下执行 `mkdir -p .claude/DEEPSHIP`，然后从全局 `~/.claude/DEEPSHIP/` 拷贝 `Prompt.md`、`Plan.md`、`Documentation.md` 三个模板。

**自验证**：`python checks/verify.py` 检测跨文件引用漂移、状态机一致性、模板污染和文件大小。

## 安装

```bash
# DEEPSHIP 是全局 harness，放在 ~/.claude/DEEPSHIP/
# Claude Code 通过 ~/.claude/CLAUDE.md 中的索引加载
```

## 版本管理

- 按 Plan.md 中 milestone 的版本变化记录
- `Documentation.md` §4 记录每次变更类型和影响

## 与 Claude Code Harness 的双向关系

DEEPSHIP 是**全局开发框架**（唯一真相源），Claude Code 的以下组件**索引或派生**自 DEEPSHIP：

| 组件 | 关系 | 维护规则 |
|------|------|----------|
| `~/.claude/CLAUDE.md` | **索引指针** → DEEPSHIP | DEEPSHIP 目录结构变化时同步更新 |
| `~/.claude/rules/common/*.md` | **派生规则** ← DEEPSHIP §B/C | DEEPSHIP 的代码规范/安全约束变更时须检查这些文件是否需要同步 |
| `~/.claude/settings.json` | 独立配置，不影响 DEEPSHIP | DEEPSHIP 推荐 tool/skill 但配置属于 harness 层 |

**修改 DEEPSHIP 时的检查清单：**
- [ ] 如果改了工具索引（`implement/tools.md`）：检查是否有新 agent/skill 需要注册
- [ ] 如果改了代码规范（`implement/code-style.md`）：同步 `rules/common/coding-style.md`
- [ ] 如果改了安全约束（`implement/safety.md`）：同步 `rules/common/security.md`
- [ ] 如果改了状态机/会话规则（`implement/state-machine.md`）：同步 `CLAUDE.md` 中的索引描述
- [ ] 如果文件结构变了：更新 `README.md` + `CLAUDE.md` 的表格
- [ ] 改完跑 `python checks/verify.py`

## 许可

MIT
