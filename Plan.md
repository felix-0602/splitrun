# Plan.md — Milestone 切片与执行计划

> **用途**：基于 Prompt.md 的目标和 Reality Scan 的结果，拆解可执行的 milestone。
> **更新频率**：每个 milestone 完成后更新进度；Reality Scan 在计划制定前更新。
> **读者**：AI（自治执行）+ 人（验收复盘）。
> **每个项目一份**：本文件是模板。新项目拷贝到 `<项目>/.claude/DEEPSHIP/Plan.md`。
> `.claude/DEEPSHIP/checks/` 目录用于存放项目**临时验证脚本**——写、跑、验证、删。不复用的不进测试套件，不累积历史遗物。约定详见 `implement/tools.md` A.3.1。

---

## Project Reality Scan

| 项 | 当前事实 | 证据位置 | 影响 |
|----|----------|----------|------|
| 用户入口 | [用户从哪开始] | [browser/js/curl/file:line] | [对方案的影响] |
| 内容入口 | [关键页面/步骤] | [实测证据] | [跨域/权限等影响] |
| 当前调用链路 | [entry → ... → render] | [代码位置] | [目标与现状的差距] |
| 核心数据 | [关键 selector / API / 字段] | [实测] | [对实现的约束] |
| 既有断点 | [已被确认但未修复的问题] | [file:line / issue] | [哪些留到后续] |

---

## Milestone 依赖图

```
M1: [名称]
 |
 +---> M2: [名称]
 |
 +---> M3: [名称]
```

---

## M1: [Milestone 名称]

- **目标**：[一句话，可观测的行为]
- **依赖**：[依赖的 M0 或其他前置条件]
- **建议 Effort**：`high` / `medium` / `low`
- **预估文件数**：~[N] 个
- **主导质量维度**：[🎨 UX / 🛡 Security / ⚡ Performance / 🏗 Architecture / 🧩 Module Depth / 🔒 Data Integrity / 🔭 Observability / 🚀 DevOps]
- **质量门禁**：[通过条件]
- **文档影响**：[哪些文档需要更新]
- **版本影响**：[none / patch / minor / major]

### Acceptance Criteria
- [ ] AC1: [具体可验证的条件]
- [ ] AC2: [具体可验证的条件]

### Reality Links
- **覆盖的用户入口/链路**：[入口 → 链路]
- **修复的既有断点**：[断点描述]
- **不覆盖的相关断点**：[以及为什么]

### Real Acceptance Scenarios
- [ ] [真实验收场景]

### Validation Commands
```bash
[验证命令]
```

### Documentation & Version Tasks
- [ ] [文档更新任务]
- [ ] [版本更新任务]

### Residual Risks
- [ ] [剩余风险]

---

## 进度总览

| Milestone | 状态 | Effort |
|-----------|------|--------|
| M1 | ⬜ pending | — |
| M2 | ⬜ pending | — |
