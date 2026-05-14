# Intent-Aware Profiles

> **在 READ_CONTEXT 时加载。** 根据用户意图信号激活对应 profile，调整状态机严格度。

## Profile 定义

| Profile | 激活状态子集 | 触发信号 |
|---------|-------------|---------|
| `development`（默认） | 完整 11 状态链路 | 无特殊信号，或含"开发/实现/构建/重构/添加/修改" |
| `deployment` | READ_CONTEXT → EXECUTE → RECORD → ADVANCE | "部署/发布/上线/land/deploy/ship/merge" |
| `debug` | READ_CONTEXT → MAP_REALITY → EXECUTE → VALIDATE → RECORD → ADVANCE | "调试/debug/修/修复/fix/为什么/排查/调查/bug/investigate" |
| `skill` | 绕过状态机 | 用户显式 `/skill-name` 调用，或"用 XX 技能/查一下/搜一下/帮我看看" |
| `learning` | 绕过状态机 | "解释/讲解/教我/什么是/怎么理解/review/code review/审查/检查" |

## 各 Profile 行为规则

### development（默认）

- 状态机：完整 11 状态，无跳过
- 工具权限：按 protocol/policy.md 权限矩阵
- Guard：全部生效

### deployment

- 状态机：READ_CONTEXT → EXECUTE → RECORD → ADVANCE
- 跳过：CLARIFY_INTENT, MAP_REALITY, SELECT_MILESTONE, PLAN_STEP, VALIDATE
- 约束：EXECUTE 仍受 files_allowed 限制；RECORD 前必须写 Documentation.md §4/§7
- 安全网：禁止跳过 security-reviewer 触发词检查

### debug

- 状态机：READ_CONTEXT → MAP_REALITY → EXECUTE → VALIDATE → RECORD → ADVANCE
- 跳过：CLARIFY_INTENT, SELECT_MILESTONE, PLAN_STEP
- 约束：MAP_REALITY 必须完成（Reality-First 不可跳过）；VALIDATE 必须运行
- 安全网：EXECUTE 仍受 files_allowed 限制

### skill

- 状态机：完全绕过
- 工具权限：**所有工具放行**，不拦截
- 适用：用户显式调用的 skill、纯查询请求
- 安全网：无（信任 skill 自身的约束）

### learning

- 状态机：完全绕过
- 工具权限：**所有工具放行**，不拦截
- 适用：代码审查、讲解、教学、review
- 安全网：无（学习/审查场景不需要门禁）

## Profile 选择优先级

1. 用户显式声明（"用 X profile"）→ 直接激活，最高优先
2. skill 显式调用（`/skill-name`）→ `skill`
3. 意图关键词匹配 → 按上表
4. 无匹配 → `development`

## 硬约束（所有 profile 通用）

- **Reality-First 不可跳过**：debug profile 保留 MAP_REALITY；deployment 跳过需承担风险
- **安全审查不可跳过**：auth/用户输入/DB/文件/API/加密/支付触发词命中时，即使 skill/learning profile 也必须调 security-reviewer
- **向后兼容**：无 profile 字段时默认 development，行为与旧版完全一致
