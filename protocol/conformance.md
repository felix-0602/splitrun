# DEEPSHIP 一致性协议

> **权威协议层。** 定义 runtime 实现如何证明自己符合 DEEPSHIP 协议。
> 这是 DEEPSHIP 的"产品核心"：任何 runtime（Mate、Claude Code hook、未来实现）只要能通过所有 cases，就能声称实现了 DEEPSHIP。

## 一致性等级

| 等级 | 要求 | 含义 |
|------|------|------|
| **Level 1 — Policy** | 通过 `tests/conformance/policy_cases.json` 全部 cases | Policy Engine 正确拒绝违规工具调用 |
| **Level 2 — Transition** | 通过 `tests/conformance/transition_cases.json` 全部 cases | 状态机转移和 guard 正确 |
| **Level 3 — Work Unit** | 通过 `tests/conformance/work_unit_cases.json` 全部 cases | WU 生命周期、并行分派、子代理回收和集成准入完整 |
| **Level 4 — Persistence** | 通过 `tests/conformance/persistence_cases.json` 全部 cases | 持久化格式和初始化正确 |

## Case 格式

每个 case:
```json
{
  "name": "描述",
  "state": "当前状态",
  "tool": "工具名",
  "args": {},
  "work_unit": {} | null,
  "workspace": "/ws" | null,
  "expected": "ALLOW" | "BLOCK",
  "reason": "为什么"
}
```

## 实现者清单

声称实现 DEEPSHIP Level N 之前：

1. 搭建测试 harness：读 `tests/conformance/*.json`，对每个 case 调用 `Policy.evaluate(tool, args, state, context)`
2. 全部 `expected` 匹配 → 通过
3. 任一 case 不匹配 → 不通过，必须修复 Policy Engine 或更新 case（如 case 有误）
4. 通过后更新 `adapters/<name>/README.md` 标明等级和日期

Level 3 实现还必须证明：
- 可并行 WU 的 `files_allowed` 不重叠且依赖已满足
- 子代理结果的 `changed_files` 全部位于自己的 `files_allowed`
- 子代理不得修改 `.deepship/state.json` / `.deepship/work_units.json` / `.deepship/log.jsonl`
- `integrated` 只能由主线程在验证通过后写入

## 参考实现

- **Mate**：Python runtime，完整 ToolRegistry + StateStore + Policy Engine。目标 Level 4。
- **Claude Code adapter**：`adapters/claude-code/`，PreToolUse hook 实现。目标 Level 1（Policy）。

## 新增 Case

发现新的协议漏洞 → 先加 case（`tests/conformance/`），再现修协议文档（`protocol/`），最后通知实现者更新。
