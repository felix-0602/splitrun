# DEEPSHIP 持久化协议

> **权威协议层。** 定义 `.deepship/` 下所有文件的格式、读写时机和完整性约束。
> Runtime 的 StateStore 必须实现此协议。

## 文件清单

| 文件 | Schema | 读 | 写 |
|------|--------|----|----|
| `.deepship/state.json` | `schemas/state.schema.json` | READ_CONTEXT 必读 | RECORD 必写 |
| `.deepship/work_units.json` | `schemas/work_unit.schema.json` | SELECT_MILESTONE, EXECUTE | PLAN_STEP, RECORD |
| `.deepship/log.jsonl` | `schemas/log.schema.json` | READ_CONTEXT（最后 10 行） | RECORD 必追加 |

## state.json 格式

```json
{
  "current_state": "READ_CONTEXT",
  "current_milestone": "M1",
  "current_work_unit": "WU-002",
  "last_completed_state": null,
  "next_action": "读取 Plan.md 确定当前 milestone",
  "validation_status": null,
  "updated_at": "2026-01-01T00:00:00Z"
}
```

### 字段约束
- `current_state` MUST 是合法状态名
- `validation_status` MUST 是 `null` / `"passed"` / `"failed"`
- `updated_at` MUST 是 ISO 8601 UTC

## work_units.json 格式

```json
{
  "milestone": "M1",
  "work_units": [
    {
      "id": "WU-001",
      "goal": "实现用户登录",
      "scope": "仅 auth 模块",
      "files_allowed": ["src/auth/login.ts"],
      "depends_on": [],
      "acceptance_tests": ["npm test -- auth"],
      "risk_level": "medium",
      "owner": "orchestrator",
      "status": "integrated",
      "validation_evidence": "pytest: 12 passed",
      "integration_status": "merged, VALIDATE passed",
      "created_at": "2026-01-01T00:00:00Z",
      "updated_at": "2026-01-01T01:00:00Z"
    }
  ]
}
```

### 状态约束
- `status` MUST 是: `pending` | `in_progress` | `done` | `integrated` | `blocked` | `failed`
- `done` MUST NOT 出现在 COMPLETE 准入检查中——只有 `integrated` 允许
- `files_allowed` MUST NOT 为空
- `owner` MUST NOT 为空

## log.jsonl 格式

每行一条 JSON，每次状态转移追加一行。

```json
{"from_state":"READ_CONTEXT","to_state":"MAP_REALITY","reason":"目标已明确","evidence":"grep: 3 入口文件","validation_commands":[],"result":"ok","timestamp":"2026-01-01T00:00:00Z"}
```

### 字段约束
- `from_state` / `to_state` MUST 是合法状态名
- `timestamp` MUST 是 ISO 8601 UTC
- `result` MUST 是 `ok` / `fail` / `blocked`

## 初始化

新项目首次使用时，MUST 执行以下初始化：

1. `mkdir -p .deepship`
2. 写入 `state.json`（初始 `current_state: "READ_CONTEXT"`）
3. 写入 `work_units.json`（空 WU 列表）
4. 写入 `log.jsonl`（种子行：`{"init":true,"timestamp":"..."}`）

Runtime 在 READ_CONTEXT 时检测 `.deepship/` 是否存在——不存在则自动初始化。
## Dynamic Planning Artifacts

These files are PLAN_STEP outputs used for new-session arbitration and prompt
alignment:

| File | Schema | Read | Write |
|------|--------|------|-------|
| `.deepship/sessions.json` | `schemas/session_registry.schema.json` | READ_CONTEXT, PLAN_STEP | PLAN_STEP |
| `.deepship/plan-revisions/*.md` | Markdown | PLAN_STEP | PLAN_STEP |
| `.deepship/a2a/*.json` | `schemas/a2a_contract.schema.json` or arbitration payload | PLAN_STEP | PLAN_STEP |
| `.deepship/prompt-supplements/*.md` | Markdown | READ_CONTEXT, PLAN_STEP | PLAN_STEP |

When a new conversation enters a project with an active owner session, it MUST
produce these artifacts before creating an additional lane/worktree. The
artifacts align the plan revision, A2A interface, validation contract, and
prompt supplement so later integration does not depend on stale assumptions.
