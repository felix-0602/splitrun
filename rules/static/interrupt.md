# Interrupt Routing — JIT Rule

## 进入条件

用户消息为 Small+，且当前有活跃 lane 正在执行时触发。

## 流程

1. **暂停当前 lane** — 设置 `_interrupt_pending=true`
2. **归一化意图** — 调用 `IntentClassifier.normalize_intent()`
3. **路由决策** — 调用 `InterruptRouter.route()`
4. **执行路由** — 根据 RouteType 采取行动
5. **协调** — 调用 `Reconciler.reconcile()`

## 路由处理

### CACHE_ANSWER
- 直接从上下文回答，不修改任何文件
- 设置 `_interrupt_reconciliation=pause`（临时暂停，答完后可 continue）

### SMALL_CONTEXT_TASK
- 构建 A2A handoff payload
- 委派给 mate/child task
- 设置 `_interrupt_reconciliation=delegated`

### NEW_LANE_LONG_TASK
- 使用 `adapters.lane.LaneManager.create(name)` 创建新 lane
- 写入 handoff payload 到 lane home
- 设置 `_interrupt_reconciliation=continue`（原 lane 继续）

### MODIFY_CURRENT_PLAN
- 修改当前 lane 的 plan/work_units
- 设置 `_interrupt_reconciliation=plan_updated`

## 禁止事项

- 不得绕过 interrupt routing 直接继续执行
- 不得在 interrupt pending 时进入 EXECUTE
- `--clear-interrupt` 仅可在 READ_CONTEXT 使用
