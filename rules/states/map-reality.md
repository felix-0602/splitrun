# MAP_REALITY 检查表

> **硬门禁：未确认以下信息，不得选定 milestone、不得写代码。**

## 必须确认

- [ ] **用户入口**：实际从哪个页面/组件/命令/API 进入？（Grep 确认 file:line）
- [ ] **调用链路**：入口 → API client → endpoint → service → DB/外部服务（Read 关键文件确认）
- [ ] **当前契约**：接口签名、响应字段、数据 schema 的实际状态（不是"应该是"）
- [ ] **消费字段**：前端/调用方实际用了哪些字段？（Grep 确认）
- [ ] **既有断点**：目标路径上已存在但未修复的问题（Documentation.md 或 Grep TODO/FIXME）
- [ ] **验收链路**：用户完成目标时应观察到什么 UI/状态/日志/数据变化

## 工具选择

| 场景 | 工具 |
|------|------|
| 快速搜代码/文件 | `Grep`, `Glob` |
| 读关键文件 | `Read` |
| 深度探索 | `Agent(Explore)` |
| 追踪执行路径 | `Agent(code-explorer)` |

## 退出条件

- [ ] 能说出端到端链路和所有断点 → SELECT_MILESTONE
- [ ] 关键链路无法确认 → BLOCK（记录未知项）
