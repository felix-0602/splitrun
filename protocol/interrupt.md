# DEEPSHIP Interrupt Routing Protocol v1.0

## 概述

中断路由层在用户中途打断活跃 lane 时介入，暂停当前执行，归一化需求，做出路由决策，并在处理完成后协调 lane 状态。

## 消息流

```
用户消息（Small+）→ InterruptDetector → IntentClassifier → InterruptRouter → Reconciliation
```

## 路由类型

| 类型 | 暂停 lane | 处理方式 |
|------|-----------|---------|
| CACHE_ANSWER | 否 | 直接从上下文回答 |
| SMALL_CONTEXT_TASK | 是 | 委派给 mate/child，附带 A2A handoff |
| NEW_LANE_LONG_TASK | 是 | 创建新 lane，附带完整 handoff |
| MODIFY_CURRENT_PLAN | 是 | 修改当前 lane 的 plan 后继续 |

## A2A Handoff Payload 格式

```json
{
  "original_input": "...",
  "normalized_intent_summary": "...",
  "lane_summary": "...",
  "plan_summary": "...",
  "constraints": [...],
  "expected_output": "...",
  "should_not_do": [...],
  "delegated_wu_id": "...",
  "created_at": "ISO"
}
```

## 协调结果

| 结果 | 含义 |
|------|------|
| continue | 中断处理完成，继续原 lane |
| pause | lane 保持暂停，等待外部输入 |
| superseded | 原 lane 被新目标替代 |
| plan_updated | lane plan 已修改，继续执行 |
| delegated | 等待 mate/lane 返回结果 |

## 状态标记

state.json 中的运行时标记（`_` 前缀，不影响状态机状态）：

- `_interrupt_pending`: 是否有未处理的中断
- `_interrupt_type`: 路由类型
- `_interrupted_lane`: 被中断的 lane 名称
- `_interrupt_intent`: 归一化后的用户意图
- `_interrupt_reconciliation`: 协调结果

## 清除中断

```bash
python adapters/cc/transition_state.py --clear-interrupt
```
