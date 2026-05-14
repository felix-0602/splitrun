# ADVANCE 检查表

## 准入条件（全部满足才能 ADVANCE）

- [ ] 当前 milestone 所有 AC 满足
- [ ] VALIDATE 全部通过（有当前消息输出为证）
- [ ] **关键路径有自动化测试覆盖，且在本 milestone 执行过（至少一次）**
- [ ] 文档已同步（用户入口/API/配置/schema 变化已反映到对应文档）
- [ ] 版本影响已记录（none / patch / minor / major）
- [ ] code-reviewer 已调（Medium+ 必调；Trivial/Small 豁免须 RECORD 写明）

## 无测试证据 → 禁止 ADVANCE

回到 `EXECUTE` 补测试。仅以下可豁免：
- 纯配置变更（.gitignore / package.json 依赖声明）
- 纯文档修改
- 纯 UI 样式调整（颜色/间距/字体）
- **豁免必须在 RECORD 时写明理由**

## 交付总结（D.6.6 格式）

```
本轮交付：[milestone 名称]
已实现：
  - [用户能做什么，具体可观测]
  - [改了什么，文件范围]
已知局限：
  - [边界情况、未覆盖场景、性能天花板]
需要你决策：
  - [产品级问题，不能代你判断；无则写"无"]
```

## 完成后（可恢复分段自治 — 自动续推）

ADVANCE 完成后，transition_state.py 自动检测 `work_units.json` 中 pending WU 并写入 `state.json`：

- [ ] 检查 `state.json` 的 `next_action` 字段（由 transition_state.py ADVANCE guard 自动写入）
  - `continue_next_wu` → **必须**在 READ_CONTEXT 后立即进入 EXECUTE（`next_wu` 指向下一个 WU），不允许等待用户输入
  - `await_user` → `continuation_mode` 非 normal，暂停等待用户确认
  - `blocked_on_deps` → 检查 `_blocked_wus`，先处理依赖阻塞再继续
  - `milestone_complete` → 当前 milestone 全部 WU integrated，进入 SELECT_MILESTONE 或 COMPLETE
- [ ] `continuation_mode: normal` 的 WU 链路**自动推进**——这是 block 纪律级别的强制规则，不依赖模型判断
