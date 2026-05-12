# Claude Code Adapter 局限性

## 不可绕过的限制

1. **CC 不支持 `transition_state` 工具。** 状态转移完全依赖模型自律——模型可以跳过 VALIDATE 直接声称 ADVANCE。

2. **CC 的 PreToolUse hook 是 adapter 级门禁，不是 DEEPSHIP 核心 runtime。** 在支持 `permissionDecision: deny` 的 CC 环境里可以拒绝工具调用；但 hook 仍可能被用户关闭、配置错误，或覆盖不完整。

3. **CC 没有 StateStore。** `.deepship/*` 的读写走原生 Read/Write/Edit 工具，无 schema 验证，无原子性保证。

4. **CC 没有 DEEPSHIP 自带的 workspace 隔离。** 路径边界依赖 hook、settings 和用户运行环境，不是协议层天然强制。

5. **子代理边界需要主线程回收验证。** 子代理可能越界修改文件；DEEPSHIP 要求主线程检查 `changed_files ⊆ files_allowed`，不满足就拒绝标记 `done/integrated`。

## 这意味着什么

在 CC 中使用 DEEPSHIP，你得到的是：
- 一个结构化的开发协议（状态、WU、持久化）
- 跨会话状态恢复能力
- hook 层的拦截增强
- 协议自洽性验证
- 子代理分工、回收、集成的标准验收集

你得不到的是：
- 强制执行的状态门禁
- DEEPSHIP 自带的不可绕过文件边界
- 自动状态转移
- workspace 安全隔离

**需要完整硬执行 → 使用 Mate（`adapters/mate/`）或等价 runtime。**
