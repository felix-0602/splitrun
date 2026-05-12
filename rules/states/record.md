# RECORD 检查表

## 持久化状态更新（必须，不可跳过）

**RECORD 的核心职责是把运行时状态写回文件系统，实现可恢复。**

- [ ] **`.deepship/state.json`**：更新 current_state / current_milestone / current_work_unit / last_completed_state / next_action / validation_status / updated_at
- [ ] **`.deepship/work_units.json`**：更新所有状态变更的 WU（done / integrated / blocked / failed）
- [ ] **`.deepship/log.jsonl`**：追加一行状态转移记录（from_state / to_state / reason / evidence / result / timestamp）。格式见 `rules/protocols/log-format.md`

## Work Unit 集成

子代理返回后，RECORD 负责回收——但**全局验证已在 VALIDATE 完成**。RECORD 只记录结果：

- [ ] 确认 VALIDATE 已通过（检查 `validation_status` 字段）
- [ ] 检查 changed_files 是否在 `files_allowed` 内 → 越界 = 回退并记录（此检查应在 EXECUTE 子代理回收时已完成）
- [ ] 更新 WU 状态：`done` → `integrated`，填写 integration_status
- [ ] 子代理 done ≠ milestone done——`done` 的 WU 必须在 RECORD 升级为 `integrated` 才能进入 COMPLETE

## 必须更新 Documentation.md

- [ ] **当前进度**（§1）：milestone 状态、完成率、时间戳
- [ ] **运行记录**（§7）：本轮做了什么、验证结果、剩余风险
- [ ] **已知问题**（§5）：新发现的问题、遗留的技术债

## 按需更新

- [ ] **技术决策**：重要选择写进 §2，完整 ADR 写进 `decisions/`
- [ ] **文档与版本**（§4）：用户可见变化、API/数据契约变化、版本影响
- [ ] **阻塞**：原因、已尝试动作、需要什么外部输入
- [ ] **审批记录**（§9）：不可逆操作

## 记录密度

- [ ] Documentation.md 保留 5-10 行高信号摘要
- [ ] 长输出、重复日志不堆在 Documentation 里
- [ ] ADVANCE 时必须写交付总结（D.6.6 格式）

## 规则弹性：豁免必须记录原因

跳过 TDD / 自审 / 需求门禁 / 交付总结时，必须写明理由。连续跳过 = 空转信号。
