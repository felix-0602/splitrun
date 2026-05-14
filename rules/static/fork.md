# Fork 执行纪律

> 进入 EXECUTE 时，如有 `execution_mode=fork` 的 WU 组，必须加载本文件。

## fork 前硬门槛（任一不满足 → 不能 fork）

- [ ] 同组 WU ≥ 2，全部 `status: pending`
- [ ] `depends_on` 已全部满足
- [ ] `files_allowed` 互不重叠
- [ ] 工作区干净或可安全创建 worktree

## fork 命令

```bash
python adapters/parallel/dispatcher.py --mode auto      # 分派
python adapters/parallel/collector.py                    # 回收（检查）
python adapters/parallel/collector.py --apply --cleanup  # 回收（应用）
```

## fork 后强制 collector（不能跳过）

- [ ] 每个 fork WU 必须有 `result.json`
- [ ] collector 验证：边界 + 测试覆盖 + 格式 + 跨 WU 冲突
- [ ] 通过后 `--apply` 合并变更
- [ ] 全局 VALIDATE 通过后才能进入 RECORD
- [ ] `transition_state.py --to VALIDATE` 会检查 fork WU 是否有 result.json（无 → 拒绝）

## 失败路径

- worker result `done + valid` → collector apply → VALIDATE
- worker result `failed` 或 invalid → REPAIR 或 PLAN_STEP
- 跨 WU 冲突 → PLAN_STEP 重新拆解
