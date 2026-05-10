# 安全约束 & 风险边界

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


---

# Effort Level 分级指南

> 当前环境：`deepseek-v4-pro[1m]` @ `effortLevel: high`（默认）

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

