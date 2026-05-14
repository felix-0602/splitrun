# coordination/session-owner: Session 所有权

**防止什么危害**：多个会话同时写同一项目的 `.deepship/` 元数据，导致状态冲突。

**为什么存在**：当存在活跃 lane 时，根项目的 `.deepship/` 元数据（state.json, work_units.json, log.jsonl）是共享状态。如果两个会话同时修改，写入会互相覆盖。Session ownership 确保同一时间只有一个会话（owner）有权修改根元数据。

**不遵守的后果**：
- 会话 A 标记 WU-001 integrated，同时会话 B 回退 WU-001 到 failed → 最终状态取决于写入顺序
- 两个会话同时更新 state.json → 后写的覆盖先写的，丢失状态转移记录

**正确路径**：新会话启动时 `--auto-recover` 或 `session.py claim_ownership` 声明所有权。旧会话的写入会被 hook 拒绝（generation mismatch）。
