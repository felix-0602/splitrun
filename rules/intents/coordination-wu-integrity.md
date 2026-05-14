# coordination/wu-integrity: WU 状态转移完整性

**防止什么危害**：WU 状态随意跳跃、进行中的 WU 被静默删除。

**为什么存在**：每个 WU 的状态机有合法路径：`pending → in_progress → done → integrated`。不允许 `pending → integrated` 跳过中间步骤，因为"集成"意味着代码已合并+测试已通过+review 已完成——跳过这些步骤的 WU 没有质量证据。同样，不允许删除 `in_progress` 或 `done` 的 WU——这相当于丢弃进行中的工作。

**不遵守的后果**：
- WU 从 pending 直接跳到 integrated → 代码没写但被标记完成 → 下一 milestone 缺功能
- 删除正在执行的 WU → 工作丢失，但没人知道为什么
- done → pending（回退已完成的工作）→ 代码已合并但标记为未开始

**例外**：已 integrated 的 WU 在 milestone 变更或 state_write 状态下允许被归档（删除），因为工作已完整合入。
