# VALIDATE 检查表

## 验证铁律

```
IDENTIFY（确定证明命令）→ RUN（完整执行）→ READ（读全部输出）
  → VERIFY（输出确认了声称吗？）→ CLAIM（才能说通过）
```

"应该能过" / "看上去对" = 撒谎。没在当前消息里跑过 = 不能声称通过。

## 验证顺序

1. [ ] Plan.md 当前 milestone 明确列出的验证命令
2. [ ] 仓库声明的脚本（package scripts / Makefile / pytest / cargo / go test）
3. [ ] 最小相关验证：本次改动影响的模块/测试
4. [ ] 边界验证：输入校验、错误路径、权限边界
5. [ ] 架构自省：模板污染？契约同步？项目隔离？文档版本同步？
6. [ ] 收尾验证（milestone 收尾或高风险改动）：全量 lint/type/build/test

## 失败处理

- [ ] 验证失败 → REPAIR（最多连续 3 轮）
- [ ] 不得通过删除关键断言、跳过真实场景、放宽断言来"通过"
- [ ] 连续 3 次修复仍失败 → BLOCK（附带 snapshot）

## 测试策略

- [ ] 关键路径有自动化测试
- [ ] 新增/修改逻辑有对应测试
- [ ] 不允许为了让测试通过而删除关键断言
- [ ] 修 bug 时先补能复现失败的测试

## Evaluator 使用边界（D.5）

- Evaluator 是辅助发现遗漏的工具，**不是最终裁判**
- [ ] 不得把 evaluator 分数作为唯一完成标准 → 以 Prompt.md Done When 和 Plan.md AC 为准
- [ ] 修复 evaluator 问题时先判断真实风险 → 形式要求优先记录取舍，不堆无意义抽象
- [ ] Evaluator PASS 后仍需检查权限/错误路径/数据一致性/可观察性

## 工具

| 场景 | 工具 |
|------|------|
| 完成前自检 | `Skill(verification-before-completion)` |
| 系统化调试 | `Skill(systematic-debugging)` |
| E2E 测试 | `Agent(e2e-runner)` |
| 浏览器 QA | `Skill(qa)` |
