## SPLITRUN v0.1.1

四个按需命令的并行 Lane 框架。不做常驻，只在需要时调用。

| 命令 | 角色 |
|------|------|
| `/splitrun-scope` | 任务共识对齐，判断是否值得并行 |
| `/splitrun-spawn` | 拆 WU，开隔离 worktree，并行启动 CC |
| `/splitrun-status` | 聚合 Lane 状态，判定能否 land |
| `/splitrun-land` | Boundary/Evidence/Integration 检查 + merge |

闭环: `scope → spawn → status → land`

### Self-verification

```bash
python checks/verify.py       # 烟测
python -m pytest tests/conformance/ -q  # 57 contract tests
```

### Key modules

- `adapters/gates.py` — 硬门禁（boundary/land/schema/recommendation）
- `adapters/brain/dispatch.py` — WU 分组，写 lane_plan.json（plan-only）
- `adapters/brain/monitor.py` — 读 Lane report，判定 merge/replan
- `adapters/parallel/spawn_lane.py` — 创建 worktree + 注册 lane index
- `checks/verify.py` — 框架自检（core code + lane index + scope + gates）
- `tests/conformance/` — 57 contract tests

### Conventions

- Lane index schema: `status`, `task`, `worktree`, `files_claimed`, `spawned_at`
- recommendation 字段: `spawn` | `do_not_spawn`（下划线，机器可读）
- BP: 在不破坏 contract tests 和 verify.py 的前提下改动
