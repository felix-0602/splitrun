# COMPLETE 检查表

## 准入条件（全部满足才能 COMPLETE）

- [ ] 当前用户请求已全部完成
- [ ] `.deepship/work_units.json` 中所有 WU 状态为 `integrated`（子代理 done ≠ 完成——必须经主线程集成和全局验证）。无 WU 的纯文档/配置任务除外。
- [ ] Plan.md 中无 pending milestone（或所有 milestone 已完成）
- [ ] 无遗留的已知问题需要在本轮处理
- [ ] VALIDATE 全部通过（有当前消息输出为证）
- [ ] `.deepship/state.json` 已更新
- [ ] `.deepship/log.jsonl` 已追加最终转移记录
- [ ] Documentation.md §1/§4/§7/§10 已更新

## COMPLETE 行为

1. 输出最终交付总结（D.6.6 格式）：
   - 本轮交付：[milestone 名称或"用户请求"]
   - 已实现：[具体可观测的能力]
   - 已知局限：[边界情况、未覆盖场景]
   - 需要你决策：[产品级问题，无则写"无"]
2. 更新 `.deepship/state.json`：`current_state: "COMPLETE"`, `next_action: "等待用户下一个请求"`
3. 更新 Documentation.md §1/§7/§10
4. **停止，等用户下一个请求**

## 禁止事项

- [ ] 禁止在 COMPLETE 后自动寻找新任务（空转）
- [ ] 禁止为了"遵守自治循环"而重复读文档
- [ ] 禁止输出"需要我继续吗？"——已经 COMPLETE，等用户主动提出新请求
