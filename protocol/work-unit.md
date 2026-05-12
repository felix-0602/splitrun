# Work Unit 协议

> **权威协议层。** 定义 work unit 的生命周期、状态转换和集成规则。
> 详细分派指南见 `rules/protocols/work-unit.md`（给模型阅读的分派模式）。

## WU 结构

见 `schemas/work_unit.schema.json`。核心字段：`id`, `goal`, `scope`, `files_allowed`, `depends_on`, `parallel_group`, `acceptance_tests`, `risk_level`, `owner`, `status`。

### 执行两轴模型

WU 的执行行为由两个正交轴定义：

| 轴 | 字段 | 职责 |
|----|------|------|
| 执行拓扑 | `execution_mode` | 这个 WU 怎么执行——主线程、串行、还是并行分叉 |
| 上下文续命 | `continuation_mode` | 这个 WU 能不能跨会话旋转继续 |

**`execution_mode`**：
- `inline`（默认）：主线程直接执行。Tier 1，单文件，小改动。
- `serial`：单会话串行执行。用于长任务——可能在安全点旋转。
- `fork`：同 `parallel_group` 的 WU 由 dispatcher 并行分派到独立 git worktree。

**`continuation_mode`**：
- `normal`（默认）：不旋转。单会话搞定。
- `rotatable`：允许在安全点写 `continuation.md` 后跨会话旋转。安全点定义见 §旋转安全点。

两轴可组合：`fork` WU 也可以是 `rotatable`（分叉出的 worker 如果任务很长，可以在自己的 worktree 里旋转）。`inline` 通常搭配 `normal`。

### parallel_group（fork 组名）

- `null`（默认）：不参与 fork
- 非空字符串：fork 组名。同组 WU MUST 满足：`files_allowed` 互不重叠、无相互依赖
- dispatcher 为同组 WU 同时创建 worktree，并行启动 worker
- join 由 collector 执行：同组全部 `done` → 验证 → 合并 → 标记 `integrated`

## 状态转换（MUST 遵守）

```
pending → in_progress → done → integrated
              ↓           ↓
           blocked      failed → 回 PLAN_STEP
```

- `done` MUST NOT 出现在 COMPLETE 准入中——只有 `integrated` 是合法终态（无 WU 的纯文档任务除外）
- `blocked` MUST 标记依赖或外部阻塞原因
- `failed` → MUST 回 PLAN_STEP 重新拆解，不可直接修改 WU 为 `integrated`

## 创建规则

- 每个 milestone MUST 拆为 ≥1 个 WU
- `files_allowed` MUST NOT 为空
- 互不依赖的 WU MAY 并行分派（`files_allowed` 互不重叠 且 `depends_on` 均为空）
- 有依赖的 WU MUST 串行执行

## 分派规则

- Claude Code adapter 的主路径是当前 CC 会话自主分派 WU
- 协议不要求外部调度器；外部脚本 MAY 作为 adapter 辅助，但 MUST NOT 成为 DEEPSHIP 核心依赖
- 子代理 MUST 只执行自己的 WU，并返回 changed_files / tests_run / result / risks
- 子代理返回 `done` 时，`tests_run` MUST 覆盖该 WU 的 `acceptance_tests`
- 子代理 MUST NOT 修改 `.deepship/state.json` / `.deepship/work_units.json` / `.deepship/log.jsonl`
- 主线程 MUST 回收子代理结果并决定是否进入 VALIDATE / REPAIR / BLOCK

## 旋转协议（continuation_mode = rotatable）

当 WU 标记 `continuation_mode: rotatable` 时，允许在安全点跨会话旋转。

### 旋转安全点

旋转只能在以下安全点触发（任一满足）：

| 安全点 | 条件 |
|--------|------|
| WU 子阶段完成 | 当前改动已提交或至少 `git diff` 可解释、测试已跑 |
| VALIDATE 完成 | 所有验收测试通过或失败原因已记录 |
| RECORD 集成完成 | 当前批次的 WU 已标记 `integrated` |
| BLOCK 状态 | 阻塞原因已写入 `Documentation.md`，等待外部输入 |

**禁止旋转的情况**：
- 有未保存的 diff 且意图未写入 `continuation.md`
- `execution_mode = inline`（inline 任务不应旋转）
- 测试刚跑了一半、结果未记录
- 当前文件越界修改未解释

### continuation.md 格式

旋转时必须写入 `.deepship/continuation.md`，新会话的 READ_CONTEXT 读此文件接上：

```markdown
# 旋转点 — <ISO 8601>

## 我在哪
- 状态机: <当前状态>
- 当前 WU: <WU ID>（<status>）
- 下一个 WU: <WU ID> 或 none

## 已完成
- <WU-XXX>: <一句话结果>
- <具体文件改动，让新模型不用猜>

## 当前 diff 意图
- <文件路径>: <为什么改、改到什么程度>

## 下一步必须做
1. <具体验证命令或操作>
2. <下一个要改的文件或测试>

## 注意事项
- <坑/偶发失败/上下文信息>
```

### 旋转流程

```
当前会话                      新会话
  │                             │
  ├─ 到达安全点                 │
  ├─ 写 continuation.md         │
  ├─ 写 state.json              │
  ├─ 调用 rotate.py             │
  ├─ 新终端启动                  │
  │   ├─ claude 启动             │
  │   ├─ READ_CONTEXT           │
  │   ├─ 读 continuation.md ────┤
  │   ├─ 读 state.json          │
  │   └─ 自然接上状态机          │
  └─ 旧终端可关闭                └─ 继续执行
```

## 集成规则

- 子代理返回后，主线程 MUST 检查 `changed_files ⊆ files_allowed`
- 主线程 MUST 拒绝任何修改 `.deepship/*` 元数据的子代理结果
- 主线程 MUST 运行全局 VALIDATE 后才可将 WU 升级为 `integrated`
- 子代理 `done` ≠ milestone `done`——集成权在主线程
- 集成后 MUST 更新 `state.json` 和追加 `log.jsonl`
