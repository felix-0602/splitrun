# Rotate 旋转纪律

> 进入 EXECUTE 时，如有 `continuation_mode=rotatable` 的 WU，必须加载本文件。

## 硬门禁

- [ ] `_session_wu_count ≥ 2` 且有未执行的 pending WU → **被拒绝进入 EXECUTE**，必须先 rotate
- [ ] 上下文监控显示剩余 ≤ 25% → **被拒绝进入 EXECUTE**，必须先 rotate
- [ ] 计数器在 `--clear-rotation` / `--auto-recover` / `--clear-interrupt` 时归零

## 触发条件（满足任一 → 必须旋转）

- [ ] 当前 WU `continuation_mode=rotatable`，且子阶段完成
- [ ] VALIDATE 完成，验收测试结果已记录
- [ ] RECORD 集成完成，WU 已标记 `integrated`
- [ ] BLOCK 状态，阻塞原因已写入 Documentation.md
- [ ] 上下文明显接近耗尽

## 旋转命令

```bash
python adapters/parallel/rotate.py \
  --diff-intent "<当前 diff 意图>" \
  --next-steps "<新会话下一步>"

python adapters/parallel/rotate.py --no-spawn --diff-intent "<意图>" --next-steps "<步骤>"
python adapters/parallel/rotate.py --kill-old --diff-intent "<意图>" --next-steps "<步骤>"
```

## 旋转后恢复

- [ ] rotate.py 写入 `continuation.md` + 标记 `state.json._rotation_pending = true`
- [ ] 新会话 READ_CONTEXT **必须**读取 `continuation.md`
- [ ] 确认后执行自动恢复：`python adapters/cc/transition_state.py --auto-recover`
- [ ] 清除前 `transition_state.py --to EXECUTE` 被拒绝
- [ ] `--kill-old` 可尝试平台检测杀旧终端（Windows: taskkill, Unix: pkill）

## 禁止旋转

- `execution_mode=inline`
- 有未保存 diff 且意图未写入 continuation.md
- 测试跑到一半、结果未记录
