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

### Fork WU 集成（强制）

`execution_mode=fork` 的 WU 进入 RECORD 前必须通过 collector 回收：

- [ ] 每个 fork WU 必须有对应的 `result.json`
- [ ] collector 已验证：边界（changed_files ⊆ files_allowed） + 测试覆盖 + 格式 + 跨 WU 冲突
- [ ] collector `--apply` 已将 worktree 变更合入主仓库
- [ ] 无 collector evidence 的 fork WU **不能**标记为 `integrated`
- [ ] fork WU 的 `integration_status` 必须注明 collector 验证结果
- [ ] `transition_state.py --to VALIDATE` 会检查 fork WU 是否有 result.json（无 → 拒绝）

## 必须更新 Documentation.md

- [ ] **当前进度**（§1）：milestone 状态、完成率、时间戳
- [ ] **运行记录**（§7）：本轮做了什么、验证结果、剩余风险
- [ ] **已知问题**（§5）：新发现的问题、遗留的技术债

## 按需更新

- [ ] **技术决策**：重要选择写进 §2，完整 ADR 写进 `decisions/`
- [ ] **文档与版本**（§4）：用户可见变化、API/数据契约变化、版本影响
- [ ] **阻塞**：原因、已尝试动作、需要什么外部输入
- [ ] **审批记录**（§9）：不可逆操作

### Pending Records 回收

EXECUTE/REPAIR 中不得直接写 Documentation.md。如需记录事件：

- [ ] 调用 `write_pending_record(root, event_type, message)` 追加到 `.deepship/pending_records.jsonl`
- [ ] RECORD 进入时 `transition_state.py` 自动回收 pending records 到 Documentation.md
- [ ] 回收后 pending_records.jsonl 清空

## 记录密度

- [ ] Documentation.md 保留 5-10 行高信号摘要
- [ ] 长输出、重复日志不堆在 Documentation 里
- [ ] ADVANCE 时必须写交付总结（D.6.6 格式）

## 规则弹性：豁免必须记录原因

跳过 TDD / 自审 / 需求门禁 / 交付总结时，必须写明理由。连续跳过 = 空转信号。
