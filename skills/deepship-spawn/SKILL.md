---
name: deepship-spawn
description: |
  Read confirmed scope.md, break into work units, spawn isolated Claude Code
  sessions in parallel git worktrees. Each lane gets its own worktree, task file,
  and terminal window. User confirms WU split and file boundaries before spawning.
allowed-tools:
  - Read
  - Write
  - Bash
  - Edit
  - Glob
  - Grep
  - AskUserQuestion
---

# /deepship-spawn — 并行 Lane 启动

读 `scope.md`，拆 WU，开隔离 git worktree，启动独立 Claude Code 会话。

## 前置条件

`.deepship/scope.md` 必须存在且 `recommendation: spawn`。如果不存在或 recommendation 是 `do_not_spawn`，告知用户先跑 `/deepship-scope`。

## 流程

### Step 1: 读 scope.md

确认以下字段齐全：
- Proposed WUs（≥2 个互不依赖的）
- Files Claimed（每个 WU 的文件边界明确）
- Validation Plan（每个 WU 有验证方式）

如果 scope.md 不完整，停止并告知用户需要重新 scope。

### Step 2: WU 分组

将 Proposed WUs 按依赖关系分组：
- 互不依赖的 WU → 可以进不同 Lane（并行）
- 有依赖的 WU（WU-02 depends on WU-01）→ 必须在同一 Lane 串行，或分两个 Lane 但标注依赖

每个 Lane 分配：
- lane_id（LANE-001, LANE-002...）
- 分配的 WU ID 列表
- files_claimed（该 Lane 允许修改的全部文件）
- 模型级别（simple→flash, medium→pro, complex→pro）

### Step 3: 展示拆分方案 + 用户确认

用 AskUserQuestion 展示：

```
## 并行方案

Lane N: [N个WU] — [文件范围]
  模型: [flash|pro]

文件冲突检查: [无冲突 | 有冲突需要用户裁决]

确认后将在独立 git worktree 中启动 N 个 Claude Code 会话。
```

选项：
- A) 确认，启动所有 Lane
- B) 只启动部分（用户指定哪些）
- C) 取消

### Step 4: 创建 Worktree + 启动 Lane

对每个确认的 Lane，依次执行：

```bash
# 1. 创建隔离 worktree
python -c "
from adapters.parallel.spawn_lane import LaneSpawner
spawner = LaneSpawner()
result = spawner.spawn(
    task='''[WU目标描述]''',
    files=['file1.py', 'dir2/'],
    lane_id='LANE-XXX'
)
print(f'Created: {result[\"lane_id\"]} at {result[\"worktree_path\"]}')
"
```

如果 spawn_lane.py 不可用（不在 DEEPSHIP 项目内），手动执行：
```bash
git worktree add ~/.claude/.deepship-worktrees/LANE-XXX -b lane/LANE-XXX
```

然后在 worktree 中写入 `.deepship/lanes/LANE-XXX/task.md`：
```markdown
# LANE-XXX 任务

## WUs
[从 scope.md 复制的 WU 描述]

## 允许修改的文件
[files_claimed 列表]

## 验证
[validation plan]

## 约束
- 只改 files_claimed 内的文件
- 完成后写 .deepship/lanes/LANE-XXX/report.json
- 完成写 report 后就可以关闭，Brain 会来 land
```

### Step 5: 注册 + 报告

更新 `.deepship/lanes/index.json`（如果 spawn_lane.py 没自动做）。

输出摘要：
```
已启动 N 个 Lane:
  LANE-001 — [任务简述] — [worktree路径]
  LANE-002 — [任务简述] — [worktree路径]

下一步: 在各 Lane 终端中工作，完成后用 /deepship-status 查看进度，
       全部完成后用 /deepship-land 收敛合并。
```

## 约束

- 不替 Lane 写代码
- 不修改 scope.md
- 文件冲突检测必须在 spawn 前完成
- 如果 spawn_lane.py 报文件冲突，停下来让用户裁决
