# Claude Code Adapter

> Claude Code 是 DEEPSHIP 执行纪律的一个 adapter。它能通过 prompt、JIT 规则和 hook 提升约束，但不是完整 runtime。

## What This Adapter Does

Claude Code 原生执行权仍在模型/runtime 手里。DEEPSHIP 在这里做三件事：

| Layer | Mechanism | Effect |
|-------|-----------|--------|
| Entry discipline | `core/manifest.md` | 让会话知道状态机、WU 和规则入口 |
| JIT rules | `rules/states/*.md` | 每个状态进入时加载对应检查表 |
| Write gate | PreToolUse hook | 对错误状态、越界文件、元数据写入做 adapter 级拒绝 |

这套 adapter 的价值是：让 Claude Code 在真实项目里更接近“可恢复、可验收”的工作方式，而不是每轮都从聊天上下文里猜。

## Work Loop

```text
READ_CONTEXT
  read Prompt / Plan / Documentation / .deepship state
MAP_REALITY
  inspect real files and current behavior
PLAN_STEP
  create bounded Work Units
EXECUTE
  edit only current WU files_allowed
VALIDATE
  run tests / typecheck / build
RECORD
  update .deepship state, work_units, log
ADVANCE
  continue or COMPLETE
```

## Hook Gate

The versioned hook source lives in this repository:

```text
adapters/claude-code/hooks/deepship-policy-guard.js
```

Install or update the global hook from that source:

```powershell
New-Item -ItemType Directory -Force -Path "$HOME\.claude\hooks"
Copy-Item adapters\claude-code\hooks\deepship-policy-guard.js "$HOME\.claude\hooks\deepship-policy-guard.js" -Force
```

The global hook is usually installed at:

```text
~/.claude/hooks/deepship-policy-guard.js
```

It checks Write/Edit/MultiEdit calls against:

- current `.deepship/state.json`
- current `.deepship/work_units.json`
- current WU `files_allowed`
- project root boundary

It also supports a local trusted-root file for dogfooding runtime/framework projects:

```json
{
  "trusted_write_roots": [
    "C:\\Users\\27464\\.claude\\DEEPSHIP",
    "D:\\Projects\\mate"
  ]
}
```

This only bypasses “outside current project root” blocking for explicit trusted roots. It does not remove normal `files_allowed` discipline inside a DEEPSHIP project.

## Conformance

Run:

```bash
python -m unittest tests.conformance.test_cc_hook_policy
python -m unittest tests.conformance.test_global_deepship_policy_guard
python -m unittest tests.conformance.test_bash_hook_policy
```

These tests prove the adapter hook matches the policy cases, that trusted roots do not accidentally open arbitrary external writes, and that Bash metadata writes are blocked even through multiline commands.

## Limits

- Claude Code has no DEEPSHIP-owned `ToolRegistry.execute()` hard gate.
- State transitions still rely partly on model behavior.
- Hooks can be disabled or misconfigured by the user.
- Worktree isolation only exists when using the parallel adapter.

For true hard execution, DEEPSHIP needs a runtime such as Mate to enforce the same discipline at the tool-dispatch layer.
