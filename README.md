# DEEPSHIP — 现实优先的自洽开发框架

> 全局开发 harness，适用于所有项目。基于 `.claude/DEEPSEEK/` 演进而来。

## 四文件体系

| 文件 | 职责 | 何时读写 |
|------|------|----------|
| `Prompt.md` | 项目目标、硬约束、非目标、Done When | 项目开始写定，scope 变更时更新 |
| `Plan.md` | Milestone 切片、Reality Scan、AC、验证命令 | 计划前做 Reality Scan，完成后标记 |
| `Documentation.md` | 活文档：进度、决策、已知问题、运行记录 | 每 milestone 完成后必须更新 |
| `Implement.md` | 执行手册：工具索引、安全约束、状态机、会话规则 | 发现新工具/场景时追加 |

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
- **契约同步**：改函数签名/API/env/类型/启动命令时，文档和测试是同一改动的组成部分，不是扩 diff
- **模块深度**：接口即测试面；mock 超过 2 个说明模块太浅；一个适配器的接缝是废抽象
- **TDD 内循环**：红→绿→重构，先写测试定义契约，再写最小实现
- **报错反馈**：现象→根因→修复→剩余风险，不悄悄修
- **交付总结**：milestone 完成时主动列出已实现/已知局限/需要你决策
- **双向一致**：修改 DEEPSHIP 时检查 Claude Code harness 联动的配置和规则

## 项目结构

DEEPSHIP 分两层：**全局框架**（一份）+ **项目实例**（每个项目一份）。

```
~/.claude/DEEPSHIP/                    ← 全局框架（模板 + 执行手册）
  Prompt.md                            ← 通用模板
  Plan.md                              ← 通用模板
  Documentation.md                     ← 通用模板（含框架自身演进记录）
  Implement.md                         ← 执行手册（全局共享）
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
- [ ] 如果改了 §A（工具索引）：检查是否有新 agent/skill 需要注册
- [ ] 如果改了 §B（代码规范）：同步 `rules/common/coding-style.md`
- [ ] 如果改了 §C（安全约束）：同步 `rules/common/security.md`
- [ ] 如果改了 §D（状态机/会话规则）：同步 `CLAUDE.md` 中的索引描述
- [ ] 如果文件结构变了：更新 `README.md` + `CLAUDE.md` 的表格

## 许可

MIT
