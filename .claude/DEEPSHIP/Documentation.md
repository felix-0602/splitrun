# Documentation.md — DEEPSHIP 框架演进记录

> DEEPSHIP 自身的工程状态。根目录同名文件是通用模板。

---

## 1. 当前进度

| 字段 | 值 |
|------|-----|
| 当前 Milestone | 完成（M1+M2 全部交付） |
| 状态 | stable |
| 上次更新 | 2026-05-10 |
| 框架版本 | DEEPSHIP v1.4（Superpowers 深入融合 + Ralph 管道模式） |

---

## 2. 最近决策

| 日期 | 决策 | 原因 |
|------|------|------|
| 2026-05-10 | 从 Superpowers 引入四项行为约束：CLARIFY_INTENT 硬门禁、SDD 两级审查门、验证铁律、TDD 反借口表 | 工具索引只是建议，行为约束才是"必须做"。tools.md 列了 skill 名但没封死"跳过" |
| 2026-05-10 | 从 Ralph 引入工作单元 spec 模板、合并队列规则、卡壳恢复协议 | PLAN_STEP 拆步骤太随意，缺少依赖标注和复杂度分级 |
| 2026-05-10 | Implement.md 拆为 `implement/` 目录（6 文件） | 918 行超 B.3 上限；6 个段落不同时刻读、不同目的，本就应该分开 |
| 2026-05-10 | 移除 DeepMemories | v1.0 设计，3 版本全是 .gitkeep。YAGNI |
| 2026-05-10 | 新增"契约同步原则"（C.2.1） | 区分"最小因果链条"与"扩 diff" |
| 2026-05-10 | 项目实例架构：全局模板 + `项目/.claude/DEEPSHIP/` | Plan.md 被项目内容污染 |

---

## 3. 版本记录

| 时间 | 版本 | 主要内容 |
|------|------|----------|
| 2026-05-10 | v1.4 | Superpowers 深入融合：CLARIFY_INTENT 硬门禁、EXECUTE SDD 两级审查、VALIDATE 验证铁律、TDD 反借口表 + Ralph 管道：工作单元 spec、合并队列、卡壳恢复 |
| 2026-05-10 | v1.3 | 契约同步原则（C.2.1）、项目隔离架构（.claude/DEEPSHIP/）、checks/verify.py 自验证、VALIDATE 架构自省 |
| 2026-05-10 | v1.2 | CLARIFY_INTENT 状态、TDD 内循环、并行子代理分派、Heartbeat 升级、审查分层 |
| 2026-05-08 | v1.1 | B.8 深度模块与接口设计、自然沟通系统、D.2 精简 |
| 2026-05-08 | v1.0 | 四文件体系、Reality-First 流程、状态机 |

---

## 4. 已知问题

| ID | 描述 | 状态 |
|----|------|------|
| K001 | Implement.md 918 行超 B.3 上限 | ✅ 已修复 — 拆为 implement/ 目录 |
| K002 | 状态机多源描述漂移风险 | ✅ 已缓解 — verify.py 覆盖；单源收敛待后续 |

---

## 5. 下一步

- [x] M3 完成：Level-Up 项目迁移到 `.claude/DEEPSHIP/` 架构，verify.py 全绿通过
- [ ] 后续：在新项目上从头初始化 DEEPSHIP（非迁移场景）
