# DEEPSHIP 状态转移日志格式

> `.deepship/log.jsonl` — 每行一条 JSON 记录。每次状态变化追加一行。
> 用于事后复盘、恢复状态、检查空转。

## 每行格式

```json
{"from_state":"READ_CONTEXT","to_state":"MAP_REALITY","reason":"目标已明确，开始勘察代码","evidence":"grep 找到 3 个入口文件","validation_commands":[],"result":"ok","timestamp":"2026-01-01T00:00:00Z"}
```

## 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `from_state` | string | 转移前状态 |
| `to_state` | string | 转移后状态 |
| `reason` | string | 转移原因（一句人话） |
| `evidence` | string | 支撑转移的证据（文件路径、命令输出摘要） |
| `validation_commands` | string[] | 执行的验证命令 |
| `result` | string | ok / fail / blocked |
| `timestamp` | ISO 8601 | 转移时间 |

## 恢复用途

新会话进入 READ_CONTEXT 时：
1. 读 `log.jsonl` 最后 10 行 → 理解最近状态转移路径
2. 读 `state.json` → 确定当前状态和下一步
3. 结合 Documentation.md → 获取语义上下文
4. 从 `current_state` 继续——不问用户"到哪了"
