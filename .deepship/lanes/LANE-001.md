# LANE-001: Intent-Aware Profiles

## 任务
DEEPSHIP 规则过于死板——所有场景走同一套严格状态机。需要引入 profile 系统，让规则根据用户意图自适应。

## 改什么（7 文件）

### 新建 rules/profiles.md
定义 5 个 profile 及其激活状态子集：
- development（默认）：完整 11 状态链路
- deployment：READ_CONTEXT → EXECUTE → RECORD → ADVANCE（跳过 MAP/PLAN/VALIDATE）
- debug：READ_CONTEXT → MAP_REALITY → EXECUTE → VALIDATE → RECORD → ADVANCE（跳过 CLARIFY/MILESTONE/PLAN）
- skill：绕过状态机，所有工具放行
- learning：绕过状态机，所有工具放行

### 修改 6 个文件
1. core/manifest.md — 必读表加 rules/profiles.md
2. rules/states/read-context.md — 加 profile 选择逻辑（扫描用户消息意图信号）
3. protocol/state-machine.md — 状态表加 profile 维度
4. protocol/policy.md — 权限矩阵加 profile 补充规则
5. adapters/cc/hooks/deepship_gate.py — evaluate() 加 profile 感知门禁
6. adapters/cc/transition_state.py — guard 加 profile 感知放行

## 约束
- skill/learning profile：所有工具放行，不拦截
- deployment/debug：跳过对应状态（不能用跳过当借口绕过关键 guard）
- 向后兼容：默认 development profile 行为不变
- 改完跑 python checks/verify.py
- 按 DEEPSHIP 状态机流转，独立管理你的 WU

## 开始
你已经知道自己的 lane ID 是 LANE-001。从 READ_CONTEXT 开始。
