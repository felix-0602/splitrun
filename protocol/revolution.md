# DEEPSHIP Revolution Protocol v1.0

## 概述

革命通道是当合理用户请求被 DEEPSHIP 自身框架约束拦住时的受控自进化机制。

## 触发条件

全部满足才触发：
1. 用户请求合理、合法、符合项目目标
2. 阻塞来自 DEEPSHIP 框架约束（非普通 bug）
3. 现有 interrupt routing 机制无法处理
4. 修改框架约束源码是必要的解决方式

## Revolution 流程

1. **检测阻塞** → 创建 RevolutionProposal
2. **共识弹窗** → 面向用户展示提案（原始请求、被拦位置、约束作用、改动方案、风险、审批需求、回滚方案）
3. **用户审批** → 显式"批准革命"回复
4. **自进化 lane** → 创建 self-evolution lane，修改最小必要源码
5. **审计记录** → 提案 ID、请求、约束、审批状态、修改文件、测试结果

## 硬约束

- 不允许静默修改框架约束源码
- 不允许 CC 自己批准自己
- 不允许把革命当成绕过安全规则的万能通道
- 批准前禁止任何框架源码修改

## 弹窗文案模板

```
我判断你的请求是合理的，但当前 DEEPSHIP 的一个框架约束阻止了我继续执行。
请求：...
被拦住的位置：...
这个约束原本的作用：...
我建议对 DEEPSHIP 做一次受控自进化：...
可能风险：...
需要你批准：...
请明确回复"批准革命"后我才会修改 DEEPSHIP 框架约束源码。
```

## 审计日志

每次革命事件记录到 `.deepship/log.jsonl`：
```json
{
  "type": "revolution",
  "event": "proposed|approved|rejected|lane_created|completed|rolled_back",
  "proposal_id": "<sha256-12>",
  "original_request": "...",
  "constraint_source": "...",
  "approved": true|false,
  "detail": "...",
  "timestamp": "ISO"
}
```
