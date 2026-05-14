# coordination/lane-contract: Lane 创建需 A2A 合约

**防止什么危害**：随意创建 lane/worktree 而不定义接口边界，导致并行工作无法集成。

**为什么存在**：Lane 是独立的 git worktree——它有自己的 `.deepship/`、自己的 WU、自己的状态机。如果没有 A2A contract 定义"lane 做什么、不做什么、输出什么、谁负责集成"，多个 lane 之间的冲突和重复工作就完全不可见。

**不遵守的后果**：
- 两个 lane 独立开发了同一功能 → 合并时选了错误的版本
- Lane 改的文件和主会话重叠 → merge 时才发现冲突
- Lane 完成了但没人知道它应该输出什么 → 集成时缺字段

**正确路径**：先写 `.deepship/a2a/<lane-name>.json`（包含 original_input, normalized_intent_summary, constraints, expected_output, should_not_do），再创建 lane。
