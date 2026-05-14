# Revolution Channel — JIT Rule

## 触发

当且仅当：
1. 用户请求合理
2. 被 DEEPSHIP 框架约束拦住（非普通 bug）
3. 无法通过正常路径处理
4. 修改框架源码是必要的

## 流程

1. **构建提案** — `RevolutionProposalBuilder.build_proposal()`
2. **展示弹窗** — `format_proposal_for_user()`
3. **等待审批** — 用户显式回复"批准革命"
4. **创建 lane** — `EvolutionLaneCreator.create_evolution_lane()`
5. **记录审计** — `RevolutionAudit.log_revolution_event()`

## 禁止事项

- 批准前不得修改任何 DEEPSHIP 框架约束源码
- 不得静默修改或绕过
- 不得将革命当作正常路径
- CC 不得自己批准自己
- self-evolution lane 的 files_allowed 必须严格限定为框架文件（protocol/、rules/、adapters/cc/、adapters/claude-code/hooks/）

## 回滚

如自进化导致问题：
1. git revert 对应的 self-evolution lane 分支
2. 清除 `_revolution_*` 标记
3. 记录革命审计回滚事件
