---
name: splitrun-status
description: |
  查看所有活跃 Lane 的状态——哪些 done、blocked、还在跑、越界。判定能不能 land。只读，不改任何文件。
  Triggers: 用户问"进度怎么样""做完了吗""看一下 lane""status""状态"、lane 跑了一段时间。
allowed-tools:
  - Read
  - Bash
  - Glob
  - Grep
---

# /splitrun-status — Lane 状态聚合

只读。读 `lanes/index.json` 和各 Lane 的 `report.json`，汇总状态。

## 流程

### Step 1: 读 Lane 索引

```bash
python -c "
import json
from pathlib import Path
idx = Path('.splitrun/lanes/index.json')
if idx.exists():
    data = json.loads(idx.read_text(encoding='utf-8'))
    for lid, info in data.items():
        print(f'{lid} | {info.get(\"status\",\"?\")} | {info.get(\"task\",\"?\")[:60]}')
else:
    print('NO_LANES')
"
```

如果输出 `NO_LANES`：告知用户"没有活跃 Lane，先跑 /splitrun-spawn"。

### Step 2: 读各 Lane 报告

对每个 active Lane，从 index.json 取 `worktree` 路径，读 `<worktree>/.splitrun/report.json`。

```bash
python -c "
import json
from pathlib import Path
idx = Path('.splitrun/lanes/index.json')
if idx.exists():
    data = json.loads(idx.read_text(encoding='utf-8'))
    for lid, info in data.items():
        if info.get('status') != 'active':
            continue
        wt = info.get('worktree', '')
        report_path = Path(wt) / '.deepship' / 'report.json' if wt else None
        if report_path and report_path.exists():
            r = json.loads(report_path.read_text(encoding='utf-8'))
            print(f'{lid} | {r.get(\"status\",\"?\")} | {r.get(\"result\",\"?\")[:80]}')
        else:
            print(f'{lid} | executing | (无 report — 仍在工作中)')
else:
    print('NO_LANES')
"
```

**有 report**：
- status=done → Lane 已完成
- status=blocked → Lane 被阻塞，读 `blocked_reason`

**无 report**：
- Lane 仍在执行中

**越界检测**：
如果 report 中有 `changed_files`，检查是否全部在 `files_claimed` 内。
越界的文件标为 `OUT OF BOUNDS`。

### Step 3: 聚合输出

```
## Lane 状态

LANE-001  done       [任务简述]
  changed: file1.py, file2.py  ✓ 在边界内
  tests:   3/3 passed

LANE-002  executing  [任务简述]
  尚无 report — 仍在工作中

LANE-003  blocked    [任务简述]
  reason: 依赖的库版本不兼容

LANE-004  done       [任务简述]
  changed: file3.py  ⚠ OUT OF BOUNDS: file4.py (不在 claimed 中)
  tests:   skipped
```

### Step 4: Land 判定

```
## 汇总
  2/4 done, 1 executing, 1 blocked, 1 out-of-bounds
  → CANNOT LAND — blocked lane + out-of-bounds 需先解决
```

判定规则：
- **CAN LAND**：全部 active lane 都是 done，无越界，全部有测试结果
- **CANNOT LAND — waiting**：有 lane 还在执行中（无 report）
- **CANNOT LAND — blocked**：有 lane 被阻塞，需回到 scope 重新拆解
- **CANNOT LAND — boundary**：有 lane 越界，需人工裁决
- **NOTHING TO LAND**：没有 active lane

### Step 5: 建议下一步

根据判定给出明确动作：
- CAN LAND → "跑 /splitrun-land 收敛合并"
- waiting → "等 Lane 完成后再检查"
- blocked → "回 /splitrun-scope 重新评估被阻塞的 WU"
- boundary → "确认越界改动是否需要合并到 scope，或回退越界文件"

## 约束

- 只读，不修改任何文件
- 不启动或终止 Lane
- 越界检测不自动拒绝，标记后留给 land 阶段处理
