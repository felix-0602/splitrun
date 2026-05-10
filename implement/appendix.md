# 附录：常用工具速查

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
| 不安全操作 | 触发删除、迁移、强推、付费 API 等 | 停止并请求审批 | Documentation.md §9 |
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

### 临时验证脚本（checks/）

项目 `.claude/DEEPSHIP/checks/` 是一次性验证脚本的暂存区：

| 什么时候用 | 什么时候不用 |
|------------|-------------|
| 项目特有的临时检查（验证 HTML fixture 结构、API 响应字段） | 正式测试——用 A.3.1 的测试框架 |
| 跨文件引用完整性的一次性扫描 | 可复用的测试逻辑——移入项目测试套件 |
| 部署后冒烟检查的临时脚本 | 框架自检——那是 DEEPSHIP 项目自身的 checks/ 的事 |

**铁律**：跑通后删掉。留下来的要么是正式测试（移入测试套件），要么是垃圾（删掉）。没有"暂时留着以后可能有用"。

---

> **AI 使用说明**：`implement/` 目录是操作手册，不是摆设。state-machine.md 的状态机是行为准则。遇到索引里没有的场景 → 自己判断最合适的工具 → 用完后自行追加到 tools.md 对应阶段下。safety.md 的安全自检在每次改动前过一遍。
