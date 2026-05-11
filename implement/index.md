# Implement — 执行手册（归档参考）

> **本目录为完整参考手册，不在系统提示词中加载。**
> 日常执行使用 `rules/states/` 下的 JIT 检查表（每个 21-65 行，按状态按需加载）。
> 本目录用于查询详细规则、工具映射、完整示例。

## 架构说明

DeepShip v2.1 采用 **JIT（Just-In-Time）规则加载**架构：

```
系统提示词常驻 → core/manifest.md（<70行，状态机骨架 + 规则加载触发器）
  ↓ 状态转换时 Read
rules/states/<state>.md（检查表，21-65行）
  ↓ EXECUTE 额外加载
rules/static/code-style.md + rules/static/safety.md（受益 prompt caching）
```

## 文件导航

| 你需要... | 文件 | 说明 |
|-----------|------|------|
| 查当前状态该用什么工具 | `tools.md` | A. 工具索引（状态→工具矩阵 + 按阶段索引） |
| 了解完整代码规范 | `code-style.md` | B. 代码规范（含 B.8 模块深度设计） |
| 改动前做安全自检 | `safety.md` | C. 安全约束 + E. Effort Level |
| 理解状态机完整定义 | `state-machine.md` | D. 状态机 + 沟通协议 |
| 常用速查 | `appendix.md` | 五件套、失败处理矩阵、测试策略 |

## 变更规则

- 新增工具/技能 → 追加到 `tools.md` 对应阶段
- 新增代码规则 → 追加到 `code-style.md`，同步更新 `rules/static/code-style.md`
- 安全规则变更 → 更新 `safety.md`，同步更新 `rules/static/safety.md`
- 状态机/沟通规则变更 → 更新 `state-machine.md`，同步更新 `core/manifest.md` 和对应 `rules/states/` 文件

## 优先级

文件间内容冲突时，按 `state-machine.md` D.0 的冲突处理规则裁决。
