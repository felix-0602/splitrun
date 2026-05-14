# policy/state-write: 状态写入门禁

**防止什么危害**：执行中途直接手动改 `.deepship/state.json` 绕过状态机纪律。

**为什么存在**：状态机的唯一推进入口是 `transition_state.py`——它校验合法转移 + guard 条件 + 写日志。如果模型绕过 CLI 直接 Edit state.json，就绕过了所有 guard（如 WU 未 integrated 不能 COMPLETE、REPAIR 上限 3 次等）。

**不遵守的后果**：模型可能从 MAP_REALITY 直接跳到 COMPLETE，跳过 EXECUTE、VALIDATE、RECORD，产生未经测试的代码。

**允许的状态**：READ_CONTEXT, CLARIFY_INTENT, SELECT_MILESTONE, PLAN_STEP, EXECUTE, RECORD, ADVANCE, BLOCK, COMPLETE
**禁止的状态**：MAP_REALITY, VALIDATE, REPAIR
