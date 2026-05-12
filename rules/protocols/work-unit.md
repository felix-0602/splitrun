# Work Unit Protocol

> 定义 DEEPSHIP 工作单元的创建、分派、执行和集成协议。PLAN_STEP 必须产出 work units，EXECUTE 按此协议执行，RECORD 按此协议回收。

## Work Unit 定义

每个 work unit 是 bounded execution unit——有明确的边界、验收标准和集成条件。

```json
{
  "id": "WU-<序号>",
  "goal": "<一句话目标>",
  "scope": "<边界说明：涉及什么模块，不涉及什么>",
  "files_allowed": ["<允许修改的文件列表>"],
  "depends_on": ["<依赖的 WU id>"],
  "parallel_group": "<并行组名 或 null>",
  "acceptance_tests": ["<验收测试命令或断言>"],
  "risk_level": "low | medium | high",
  "owner": "orchestrator | subagent:<name>",
  "status": "pending | in_progress | done | integrated | blocked | failed",
  "validation_evidence": "<验证输出或 null>",
  "integration_status": "<集成结果或 null>",
  "created_at": "<ISO 8601>",
  "updated_at": "<ISO 8601>"
}
```

## 创建规则（PLAN_STEP）

每个 milestone 拆为 ≥1 个 WU。PLAN_STEP 必须为每个 WU 标记两轴：

### 执行拓扑（`execution_mode`）

| 值 | 何时用 | 由谁执行 |
|----|--------|---------|
| `inline` | Tier 1 单文件小改动 | 主线程直接 |
| `serial` | 长任务、大重构、跨多文件 | 主线程串行（可配合 rotate） |
| `fork` | 可并行拆解、文件边界清晰、初始实现/plan 阶段 | dispatcher 分会话 |

**fork 保守原则**：只能在 PLAN_STEP 明确标记。不能在执行中临时"觉得可以并行"。适用场景：复杂任务可拆解、初始执行阶段文件未耦合、整体重构已定文件边界。

### 上下文续命（`continuation_mode`）

| 值 | 何时用 |
|----|--------|
| `normal` | 单会话能搞定 |
| `rotatable` | 预计跨多个会话，允许在安全点旋转 |

`rotatable` 的 WU 在安全点（WU 子阶段完成 / VALIDATE 完成 / RECORD 完成）写 `continuation.md` 后调用 `rotate.py` 旋转。格式见 `protocol/work-unit.md` §旋转协议。

### 其他规则

- 同 `parallel_group` 的 fork WU MUST：`files_allowed` 互不重叠、无相互依赖
- `execution_mode=fork` 时 `parallel_group` MUST NOT 为 null
- 有依赖的 WU 按依赖顺序执行
- 每个 WU 必须标注 `files_allowed`——子代理不得越界

## 分派规则（EXECUTE）

分派由当前 Claude Code 会话自主完成。DEEPSHIP 不要求外部调度器作为主路径；外部脚本只能作为临时实验或 adapter 辅助。

### 主线程执行（owner = orchestrator）
- 小任务、Tier 1
- 需要全局判断的集成任务
- 验证和收尾

### 子代理执行（owner = subagent:<name>）
- 大任务、Tier 2/3
- 互不依赖的并行任务
- 子代理约束：
  - 只能修改 `files_allowed` 中列出的文件
  - 不允许扩大 scope
  - 完成后必须返回：changed_files / tests_run / result / risks / integration_notes
  - `tests_run` 必须覆盖该 WU 的 `acceptance_tests`
  - 不得修改 `.deepship/state.json` / `.deepship/work_units.json` / `.deepship/log.jsonl`
  - 不负责全局验证——那是主线程的职责

## 集成规则（RECORD）

- 子代理返回后，主线程必须：
  1. 检查 changed_files 是否在 `files_allowed` 内 → 越界 = 回退
  2. 检查 changed_files 是否包含 `.deepship/*` 元数据 → 有则拒绝
  3. 检查 tests_run 是否覆盖 `acceptance_tests` → 不满足则拒绝 done
  4. 运行全局 VALIDATE（lint/type/test/build）
  5. 更新 `work_units.json`：status → `integrated`，integration_status 写集成结果
  6. 更新 `state.json` 和 `log.jsonl`
- 子代理 done ≠ milestone done——必须经过主线程集成和全局 VALIDATE

## 状态转换

```
pending → in_progress → done（子代理返回）→ integrated（主线程回收+验证）
                ↓          ↓
             blocked     failed → 回 PLAN_STEP 重新拆解
```

- `done`：子代理已完成自己的工作，但**未经过主线程集成和全局验证**。`done` 不是终态——必须由主线程在 RECORD 中升级为 `integrated`。
- `integrated`：主线程已验证、合并、记录。**这是唯一允许 COMPLETE 的终态**（无 WU 的纯文档/配置任务除外）。
- `blocked`：依赖未满足或外部阻塞
- `failed`：验证失败，需重新规划

## 并行分派条件

同时满足以下条件才可并行：
- 操作不同文件（`files_allowed` 互不重叠）
- 不共享运行时状态
- `depends_on` 均为空或已满足
- 使用 `Skill(dispatching-parallel-agents)` 分派
