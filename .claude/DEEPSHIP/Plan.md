# Plan.md — DEEPSHIP 框架开发计划

> DEEPSHIP 自身的 milestone。根目录同名文件是通用模板。

---

## Project Reality Scan

| 项 | 当前事实 | 证据位置 | 影响 |
|----|----------|----------|------|
| 验证能力 | 零——无测试、无验证脚本 | checks/ 只有刚建的目录 | 改动安全性靠人工 |
| 单点真相 | 状态机在 4 处描述 | D.1 文字+表格 + A.0 矩阵 + README 流程图 | README 漂移已被证实 |
| Project 隔离 | Plan.md 曾被 netclass-sidekick 内容污染 | git log v1.2 | 已修复 |
| 文件大小 | Implement.md 883 行 | Implement.md:883 | 超 B.3 800 行上限 |

---

## M1: 自验证 + 架构自省 — 🔵 in_progress

- **目标**：verify.py 可检测结构性退化；VALIDATE 含架构自省
- **主导质量维度**：🧩 Module Depth
- **版本影响**：minor

### Acceptance Criteria
- [ ] AC1: `checks/verify.py` 可运行，零依赖
- [ ] AC2: 跨文件引用检查（"见 X.Y" → 真实章节）
- [ ] AC3: 状态机一致性（README vs D.1）
- [ ] AC4: 模板完整性（根目录模板无项目特定数据）
- [ ] AC5: VALIDATE 含架构自省子步骤
- [ ] AC6: C.1 自检清单含契约同步和 ReAct 检查

### Validation
```bash
python checks/verify.py
```

---

## M2: 文件瘦身 — ⬜ pending

- **目标**：Implement.md 拆至 ≤ 800 行；状态机描述收敛到单源
- **主导质量维度**：🏗 Architecture

---

## 进度总览

| Milestone | 状态 | Effort |
|-----------|------|--------|
| M1 | 🔵 in_progress | high |
| M2 | ⬜ pending | medium |
