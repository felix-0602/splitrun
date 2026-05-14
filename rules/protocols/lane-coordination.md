# Lane Coordination Protocol

## Purpose

Lane coordination prevents two active DEEPSHIP sessions from silently editing the
same file. It is a hard boundary for parallel work: a lane that claims a file
owns that file until the lane is completed, paused, or released.

## Lane Index

The root session records active lanes in `.deepship/lanes/index.json`.

Each lane entry MAY include:

```json
{
  "status": "active",
  "task": "short task summary",
  "worktree": "absolute worktree path",
  "files_claimed": [
    "rules/states/read-context.md"
  ],
  "spawned_at": "ISO-8601",
  "spawned_by": "spawn_lane.py"
}
```

`files_claimed` is a list of repository-relative files or directory/pattern
claims. Active statuses are `active`, `pending`, `executing`, and
`in_progress`.

## Spawn Gate

Before creating a lane, `spawn_lane.py` MUST compare requested files against
the `files_claimed` values of all active lanes. If any requested file overlaps
an active claim, lane creation MUST fail before the worktree is created.

## Execute Gate

During `EXECUTE` or `REPAIR`, the CC gate MUST reject writes to a file claimed
by another active lane, even when the current WU `files_allowed` would otherwise
allow the write.

## Revolution Token

A revolution token is a user-approved, temporary exception for a single
`PLAN_STEP`. It is not a bypass. It only grants writes to declared paths.

```json
{
  "revolution": {
    "status": "approved",
    "allowed_paths": [
      "adapters/cc/hooks/deepship_gate.py"
    ],
    "requires_verify": true
  }
}
```

The token MAY be stored on the current WU or in `.deepship/state.json`.
The CC gate MUST allow `PLAN_STEP` writes only when `status=approved` and the
target path matches `allowed_paths`. Normal workspace and lane conflict checks
still apply outside this exact exception.

## READ_CONTEXT Trigger

If `.deepship/lanes/index.json` contains active lanes, READ_CONTEXT MUST inspect
their `files_claimed` values before planning or executing root-session writes.
