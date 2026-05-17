---
name: deepship-land
description: |
  Land parallel lanes — collect reports, run boundary/evidence/integration checks,
  merge git branches, clean up worktrees, and produce a delivery summary.
  This is the heaviest command. All three gate checks must pass before merge.
allowed-tools:
  - Read
  - Write
  - Bash
  - Edit
  - Glob
  - Grep
  - AskUserQuestion
---

# /deepship-land — 收敛、验证、合并、交付

这是闭环的最后一步，也是最重的一步。只在前置条件满足时执行。

## 前置条件

- 所有 active Lane 的 report.json 存在，且 status=done
- 无越界（或越界已被用户确认可接受）
- 建议先跑 `/deepship-status` 确认状态

## 流程

### Step 1: 收集 Lane 报告

读 `.deepship/lanes/index.json`。对每个 active Lane，从 `worktree` 字段取 worktree 路径，读 `<worktree>/.deepship/report.json`。

提取每个 Lane 的：
- `changed_files`（实际改了哪些文件）
- `test_results`（测试结果）
- `result`（完成摘要）
- `status`（必须全为 done）

如果有 Lane status != done，停止并告知用户。

### Step 2: Boundary Check — 边界检查

对每个 Lane，检查 `changed_files ⊆ files_claimed`：

```
LANE-001 boundary:
  claimed:  [file1.py, file2.py, dirA/]
  changed:  [file1.py, file2.py]
  → PASS — 全部在边界内

LANE-002 boundary:
  claimed:  [file3.py]
  changed:  [file3.py, utils/helper.py]
  → FAIL — utils/helper.py 不在 claimed 中
```

**越界处理**：
- 如果越界文件是合理的（比如 Lane 发现必须改的依赖）→ 用 AskUserQuestion 让用户确认是否接受
- 如果越界是意外的 → 用户可以选择回退该文件或重新 scope
- 用户拒绝越界 → 该 Lane 不能 land，需要回退越界改动

### Step 3: Evidence Check — 证据检查

每个 Lane 必须有：
- report.json（已完成）
- test_results 不为空（至少跑了验证）
- 如果 `test_results` 显示失败，标注原因

```
LANE-001 evidence:
  report:   ✓
  tests:    3/3 passed
  → PASS

LANE-002 evidence:
  report:   ✓
  tests:    skipped (Lane 判定为纯文档改动)
  → PASS — 合理跳过

LANE-003 evidence:
  report:   ✓
  tests:    1/3 failed
  → FAIL — 测试未通过，不能 land
```

缺少证据的 Lane 不能 land。告知用户哪些 Lane 需要补充验证。

### Step 4: Integration Check — 集成验证

所有 Lane 的 Boundary + Evidence 通过后，运行全局验证：

```bash
python checks/verify.py
```

如果项目有自己的测试套件，也运行：
```bash
# 根据项目类型自适应
python -m pytest tests/ -v --tb=short   # Python
npm test                                 # Node
# ...
```

**集成验证失败** → 不能 land。输出失败原因，让用户决定是修复还是回到 scope。

### Step 5: Merge — 合并分支

全部检查通过后，合并各 Lane 分支：

```bash
# 对每个 Lane
git merge lane/LANE-XXX --no-ff -m "merge: LANE-XXX — [任务简述]"
```

合并冲突处理：
- 如果冲突，输出冲突文件列表
- 用 AskUserQuestion 让用户选择：手动解决 / 跳过该 Lane / 取消 land

### Step 6: 清理 Worktree

```bash
# 删除 worktree
git worktree remove ~/.claude/.deepship-worktrees/LANE-XXX

# 删除 Lane 分支（已合并）
git branch -d lane/LANE-XXX

# 更新 index.json（移除已 land 的 Lane）
```

### Step 7: 写交付摘要

写入 `.deepship/land-report.md`：

```markdown
# Land Report — [时间戳]

## Summary
[本次 land 完成了什么]

## Lane Results
LANE-001: [result] — [changed_files] — [test_results]
LANE-002: [result] — [changed_files] — [test_results]

## Boundary Check
[全部 PASS | 有越界已确认]

## Evidence Check
[全部 PASS | 有缺失已标注]

## Integration Check
[verify.py + 项目测试结果]

## Merged Branches
- lane/LANE-001 → [base branch]
- lane/LANE-002 → [base branch]

## Open Issues
[如有 — 未解决的问题、需要后续关注的]
```

## 约束

- 三类检查（Boundary/Evidence/Integration）全部通过才能 merge
- 越界文件必须用户显式确认，不能自动接受
- 合并后的清理必须完整（worktree + branch + index）
- land-report.md 是交付证据，不能省略
