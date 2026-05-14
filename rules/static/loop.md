# 自治循环完整约束

> 在 READ_CONTEXT 时加载。定义激活门、自治循环规则、终止条件、恢复协议。

## 激活门（Activation Gate — 优先级最高）

**任何用户请求到达，先过此门，再决定是否进入状态机。**

| 请求类型 | 动作 |
|----------|------|
| 纯闲聊 / 问候 / "谢谢" / "嗯" | 直接回复，不进状态机 |
| Trivial（<5行, typo/格式化/单行确认，无行为变更） | 直接执行 |
| **Small+（≥5行 / 多文件 / 行为变更 / 任何需要判断的请求）** | **必须进入 READ_CONTEXT** |

**意图信号**（任一命中 → Small+，不限行数）：
- 请求涉及多个概念（功能领域、副作用、新依赖）
- 请求暗示行为变更（输出、数据流、副作用变化）
- 含技术关键词：构建/创建/重构/迁移/配置/添加/生成/更新/删除/改/修/实现/设计
- "让它工作"/"修好它"等暗示调试+验证的请求
- 同一会话中前面已提出过 Small+ 请求（惯性信号）

**判定规则**：不确定属于哪档 → 进 READ_CONTEXT。连续多个 Trivial → 合并视为 Small+。

## 自治循环规则

**DEEPSHIP 是自治循环，不是问答循环。**

| 规则 | 内容 |
|------|------|
| **自动推进** | 当前 milestone 内有 pending WU 且 `continuation_mode=normal` 时，ADVANCE guard 自动写入 `next_action: continue_next_wu` 到 state.json。READ_CONTEXT **必须**立即推进到下一个 WU 的 EXECUTE，不允许等待用户输入。这是 block 纪律级别。 |
| **终止条件** | 当前 milestone 全部 WU integrated 且无 pending milestone → `COMPLETE`（输出总结，停止） |
| **停等条件** | 仅在 BLOCK / `next_action=await_user` / Help Gradient "判断" / "需要你" 时停止 |
| **Heartbeat 不停** | Heartbeat 汇报后继续推进，除非 heartbeat 中明确声明了停等条件 |
| **上下文耗尽** | 接近窗口上限时 `transition_state.py` 硬拒绝 `→ EXECUTE`（`_is_context_critical()`），必须先 rotate |
| **强制 rotate** | `_session_wu_count ≥ 6` 或上下文 ≤ 25% 时，`transition_state.py` 硬拒绝 `→ EXECUTE`，必须先 rotate |
| **禁止空转** | `next_action=milestone_complete` 时不得为了"遵守自治循环"而重复读文档、找任务——直接 COMPLETE |

## 终止态（COMPLETE）

当以下条件全部满足时，进入 `COMPLETE` 而非 `ADVANCE`：
- 当前用户请求已全部完成
- Plan.md 中无 pending milestone（或所有 milestone 已完成）
- 无遗留的已知问题需要在本轮处理

COMPLETE 行为：
1. 输出最终交付总结（已实现 / 已知局限 / 需要你决策）
2. 更新 Documentation.md §1/§7/§10
3. **停止，等用户下一个请求**

## 恢复协议

**会话意外结束或模型在非 BLOCK 状态下停止时：**
- 新会话启动后，立即进入 READ_CONTEXT
- 读取 Documentation.md §1 确定当前进度和 milestone
- 读取 Documentation.md §7 最近运行记录，确定最后完成的操作
- **禁止**问用户"之前在哪"/"接下来做什么"——自己从文档中计算
- 如果 Documentation.md 无有效记录 → 进入 MAP_REALITY 重新勘察

## 架构诚实声明

**DEEPSHIP 自治循环的三层强制系统（Prompt + Hook + Cron）全部是影响力机制，不是机械保证。** 模型始终控制其输出。三层设计的目标是最大化自治循环约束的遵循概率——使违规可检测、可恢复，但不声称"不可违反"。

实际可靠性：Prompt 层依赖上下文窗口注意力保持；Hook 层在工具调用时机注入提醒；Cron 层定时心跳兜底。零保证需要 harness 层的状态机引擎，当前 Claude Code 架构不支持。
