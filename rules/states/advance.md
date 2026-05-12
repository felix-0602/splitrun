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

## 完成后（可恢复分段自治 — 条件推进）

- [ ] 标记当前 milestone / work unit 完成
- [ ] 检查 `.deepship/work_units.json`：是否有非终态 WU？
  - `pending` / `in_progress` → 进入下一轮 READ_CONTEXT（依赖满足时）
  - `done`（子代理返回但未集成）→ 必须先集成（RECORD），禁止直接 ADVANCE
  - `blocked` / `failed` → 先处理阻塞或回 PLAN_STEP 重新拆解
  - 全部 `integrated` + 有 pending milestone → SELECT_MILESTONE
  - 全部 `integrated` + 无 pending milestone → `COMPLETE`
- [ ] **禁止**在无任务时自动进入 READ_CONTEXT（空转）
