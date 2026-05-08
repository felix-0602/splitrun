# Plan.md — Milestone 切片与执行计划

> **用途**：把 Prompt.md 的目标拆成可独立验证的 milestone，每个有明确的 AC 和验证命令。
> **更新频率**：项目开始时生成全量计划；每个 milestone 开始前可细化；完成时标记。
> **原则**：每个 milestone 1-3 天可完成，太大就继续拆。

---

## Milestone 依赖图

> 项目开始时自动生成。用 ASCII 表示依赖关系。

```
M0: 项目脚手架 & 基础设施
 |
 +---> M1: [第一组功能]
 |       |
 |       +---> M2: [第二组功能]
 |
 +---> M3: [并行功能组]
 |
 +---> M4: 集成 & 收尾
```

---

## Project Reality Scan（计划前必做）

> 在拆 milestone 前完成。必须来自代码搜索、文件阅读、运行结果或用户提供的事实；不要只写推测。

| 项 | 当前事实 | 证据位置 | 影响 |
|----|----------|----------|------|
| 用户入口 | [页面/组件/命令/快捷键/API] | [文件路径/命令/截图] | [对目标的影响] |
| 当前调用链路 | [entry -> client -> endpoint -> service -> state/render] | [文件路径/函数名] | |
| 当前 API/契约 | [endpoint、request、response] | [文件路径/测试] | |
| 目标 API/契约 | [endpoint、request、response] | [spec/后端实现/用户要求] | |
| 契约差异 | [新增/删除/语义变化字段] | [diff/类型/schema] | |
| 前端/调用方消费字段 | [实际读取哪些字段] | [组件/状态管理/渲染位置] | |
| 后端已有能力 | [已实现 endpoint/service/tool] | [文件/测试] | |
| 管理/运营入口 | [admin/CLI/后台/API 是否存在] | [文件/路由] | |
| 文档现状 | [README/API docs/配置说明/用户手册/架构说明是否存在] | [文件路径] | |
| 版本现状 | [package/app version/tag/changelog/release notes 当前状态] | [文件路径/git 命令] | |
| 既有断点 | [不是本轮造成但阻止目标达成的问题] | [证据] | |
| 未知项 | [无法确认的信息] | [为什么无法确认] | [是否 BLOCK] |

### Reality Scan Checklist

- [ ] 用搜索确认用户入口和真实调用链路。
- [ ] 对比当前接口和目标接口的 request/response 契约。
- [ ] 确认调用方实际消费字段，而不是只看后端返回字段。
- [ ] 列出端到端目标路径上的既有断点。
- [ ] 将断点转化为 milestone、已知问题或明确的 non-goal。
- [ ] 确认可维护的文档位置和版本记录位置。
- [ ] 明确本项目版本策略：无版本、SemVer、日期版本、内部 build 号或 git tag。
- [ ] 如果关键链路无法确认，进入 `BLOCK` 或要求用户补充。

---

## Milestone 模板

每个 milestone 按以下格式编写。`[ ]` checkbox 在完成时标记为 `[x]`。

---

## M0: 项目脚手架 & 基础设施

- **目标**：[一句话]
- **依赖**：无
- **建议 Effort**：`medium`
- **预估文件数**：~N 个
- **主导质量维度**：🏗 Architecture
- **质量门禁**：[本 milestone 最重要的真实风险，例如权限、数据一致性、性能、可观察性]
- **文档影响**：[README/API/用户手册/架构/配置/无]
- **版本影响**：[none/patch/minor/major/date/build]，[原因]

### Acceptance Criteria
- [ ] AC1: [可观测的验收条件]
- [ ] AC2: [可观测的验收条件]

### Reality Links
- **覆盖的用户入口/链路**：[来自 Project Reality Scan 的具体链路]
- **修复的既有断点**：[断点 ID 或“无”]
- **不覆盖的相关断点**：[留到后续 milestone 或 non-goal]

### Real Acceptance Scenarios
- [ ] [从用户/API/系统边界出发的真实验收场景，不只验证内部字段存在]

### Validation Commands
```bash
# 先识别项目类型，再选择适用命令；不要把不适用的示例当成硬命令
# Node: npm install && npm run build && npm test
# Python: pip install -r requirements.txt && python -m pytest
# Rust: cargo build && cargo test
# Go: go test ./...

# Lint / Type Check / Build
# 使用项目实际脚本，例如 npm run lint、npx tsc --noEmit、ruff check、mypy、cargo clippy

# 运行与健康检查
# 启动项目实际 dev/server 命令，并访问 health endpoint 或等效 smoke check
```

### Documentation & Version Tasks
- [ ] 更新受影响文档，或明确说明无文档影响。
- [ ] 更新版本记录 / changelog / release notes，或明确说明无版本影响。

### Residual Risks
- [ ] [即使验证通过仍然存在的风险；没有则写“无已知剩余风险”]

---

## M1: [功能组名称]

- **目标**：[一句话]
- **依赖**：M0
- **建议 Effort**：`high`
- **预估文件数**：~N 个
- **主导质量维度**：[选一个]
- **质量门禁**：[本 milestone 最重要的真实风险]
- **文档影响**：[README/API/用户手册/架构/配置/无]
- **版本影响**：[none/patch/minor/major/date/build]，[原因]

### Acceptance Criteria
- [ ] AC1:
- [ ] AC2:

### Reality Links
- **覆盖的用户入口/链路**：
- **修复的既有断点**：
- **不覆盖的相关断点**：

### Real Acceptance Scenarios
- [ ] [真实用户/API/系统边界场景]

### Validation Commands
```bash
# 具体到这个 milestone 的验证命令
```

### Documentation & Version Tasks
- [ ] 更新受影响文档，或明确说明无文档影响。
- [ ] 更新版本记录 / changelog / release notes，或明确说明无版本影响。

### Residual Risks
- [ ] [剩余风险或“无已知剩余风险”]

---

## M2: [功能组名称]

- **目标**：[一句话]
- **依赖**：M1
- **建议 Effort**：`high`
- **预估文件数**：~N 个
- **主导质量维度**：[选一个]
- **质量门禁**：[本 milestone 最重要的真实风险]
- **文档影响**：[README/API/用户手册/架构/配置/无]
- **版本影响**：[none/patch/minor/major/date/build]，[原因]

### Acceptance Criteria
- [ ] AC1:
- [ ] AC2:

### Reality Links
- **覆盖的用户入口/链路**：
- **修复的既有断点**：
- **不覆盖的相关断点**：

### Real Acceptance Scenarios
- [ ] [真实用户/API/系统边界场景]

### Validation Commands
```bash
```

### Documentation & Version Tasks
- [ ] 更新受影响文档，或明确说明无文档影响。
- [ ] 更新版本记录 / changelog / release notes，或明确说明无版本影响。

### Residual Risks
- [ ] [剩余风险或“无已知剩余风险”]

---

## MX: 集成 & 收尾

- **目标**：端到端集成验证、文档补全、部署准备
- **依赖**：所有功能 milestone
- **建议 Effort**：`max`
- **主导质量维度**：🔭 Observability
- **质量门禁**：全部关键路径在真实或等效环境下可复现验证，评估 PASS 不能替代端到端验收
- **文档影响**：README、运行/部署说明、API/用户入口说明、已知风险必须收口
- **版本影响**：[patch/minor/major/date/build]，按本次 release 范围决定

### Acceptance Criteria
- [ ] 所有 Prompt.md 里的 Done When 条件全部满足
- [ ] E2E 测试覆盖关键用户流程
- [ ] README 有完整的运行/部署指令
- [ ] 在干净环境从头跑过一次完整验证

### Reality Links
- **覆盖的用户入口/链路**：Project Reality Scan 中所有主链路
- **修复的既有断点**：所有影响 Done When 的断点
- **不覆盖的相关断点**：必须已记录为 non-goal 或已知风险

### Real Acceptance Scenarios
- [ ] 从空环境启动项目并完成至少一条端到端核心流程
- [ ] 失败路径、权限边界、外部依赖不可用时有可观测错误和恢复策略

### Validation Commands
```bash
# 全量验证：使用项目实际脚本
# 1. install/build/lint/typecheck
# 2. unit + integration tests
# 3. E2E/visual tests（仅在项目有关键用户流或前端风险时强制）
# 4. coverage check（阈值以 Prompt.md 或本 milestone 显式要求为准）
# 5. clean environment smoke test
```

### Documentation & Version Tasks
- [ ] README/运行说明/API 契约/用户入口说明与实际行为一致。
- [ ] changelog/release notes 记录用户可见变化、破坏性变化、迁移步骤和剩余风险。
- [ ] 版本号、tag 或 build 标识符合项目版本策略。

### Residual Risks
- [ ] [上线前仍需人工验收、外部服务验证或监控跟踪的风险]

---

## 进度总览

| Milestone | 状态 | 开始 | 完成 | Effort |
|-----------|------|------|------|--------|
| M0 | ⬜ pending | — | — | medium |
| M1 | ⬜ pending | — | — | high |
| M2 | ⬜ pending | — | — | high |
| MX | ⬜ pending | — | — | max |

> 状态：⬜ pending → 🔄 in_progress → ✅ done → ❌ blocked

---

> **AI 使用说明**：每次开始新的 milestone 前，更新状态为 🔄，完成后更新为 ✅ 并记录到 Documentation.md。如果某个 AC 验证反复失败，在 Documentation.md 的"已知问题"中记录，不要跳过。
