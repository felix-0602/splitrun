# READ_CONTEXT 检查表

## 必读文件

- [ ] `.deepship/state.json` → 当前状态、milestone、next_action
  - **如果 `.deepship/` 不存在**：这是新项目。执行初始化：
    1. `mkdir -p .deepship`
    2. 从 `~/.claude/DEEPSHIP/templates/` 复制 `state.json` 和 `work_units.json`
    3. 创建空 `log.jsonl`（写入 `{"_schema":"deepship-log/1.0","init":true}`）
    4. 继续正常 READ_CONTEXT
- [ ] `.deepship/log.jsonl`（最后 10 行）→ 最近状态转移路径
- [ ] `Prompt.md` → 目标、硬约束、非目标、Done When
- [ ] `Plan.md` → 当前 milestone、AC、验证命令
- [ ] `Documentation.md` → 当前进度、已知问题、最近决策
- [ ] `rules/profiles.md` → Intent-Aware Profile 定义与选择规则

## Profile 选择（必做，不可跳过）

**读完必读文件后，扫描用户消息中的意图信号，选择对应 profile：**

| 信号 | Profile |
|------|---------|
| 用户显式声明（"用 X profile"） | 直接激活，最高优先 |
| `/skill-name` 显式调用 | `skill` |
| "部署/发布/上线/land/deploy/ship/merge" | `deployment` |
| "调试/debug/修/修复/fix/为什么/排查/调查/bug/investigate" | `debug` |
| "解释/讲解/教我/什么是/怎么理解/review/code review/审查" | `learning` |
| "查一下/搜一下/帮我看看"（纯查询） | `skill` |
| 开发关键词 或 无匹配 | `development`（默认） |

**选中 profile 后，将其写入 `.deepship/state.json` 的 `active_profile` 字段。** 所有下游状态（EXECUTE/VALIDATE/transition）从 state.json 读取 profile 来调整行为。

- `skill` / `learning`：所有工具放行，不拦截；安全触发词仍触发 security-reviewer
- `deployment`：跳过 CLARIFY/MAP/MILESTONE/PLAN/VALIDATE；EXECUTE 仍受 files_allowed 限制。**在 READ_CONTEXT 中必须创建一个最小 WU**（设置 `current_work_unit` 和 `files_allowed`），否则 transition_state → EXECUTE 的 guard 会拒绝。
  - READ_CONTEXT 下允许 `state_write`（写 work_units.json + state.json），利用此窗口创建部署 WU 再推进。
  - READ_CONTEXT 下 Bash 仅允许 git 只读命令；需要实际部署命令时先推进到 EXECUTE。
- `debug`：跳过 CLARIFY/MILESTONE/PLAN；MAP_REALITY 和 VALIDATE 保留
- `development`：完整 11 状态链路，行为与旧版完全一致

## Lane 自动发现

has_active_lanes: 如果 `.deepship/lanes/index.json` 存在 active/pending/executing/in_progress lane，先读取 `files_claimed`，不与活跃 lane 抢同一文件。

如果当前会话运行在 worktree 中（由 spawn_lane.py 或 dispatcher 启动），`.deepship/lane_id.json` 会存在：

- [ ] 检查 `.deepship/lane_id.json` 是否存在
- [ ] 如果存在：读取 `lane_id` 和 `task_summary`
- [ ] 确认 lane 身份后，读取 `.deepship/lanes/{lane_id}.md` 了解完整任务
- [ ] Lane 会话独立管理自己的状态机（不与主会话争用 state.json）
- [ ] 任务完成后，在 worktree 中写入 `result.json`，由主会话 collector 回收

## 自动续推（block 纪律级别：强制执行）

**读完 `state.json` 后，检查 `next_action` 字段。这是由 ADVANCE guard 写入的强制推进指令，不允许模型自行判断是否继续。**

- [ ] 检查 `state.json` 的 `next_action`：
  - **`continue_next_wu`**：→ **必须立即**执行以下流程，不允许等待用户输入：
    1. `python adapters/cc/transition_state.py --to MAP_REALITY`
    2. `python adapters/cc/transition_state.py --to PLAN_STEP`
    3. `python adapters/cc/transition_state.py --to EXECUTE --wu <next_wu>`
    4. 正常执行该 WU，完成后 ADVANCE 会再次写入 next_action
  - **`await_user`**：暂停。通知用户当前 milestone 还有 `_pending_wu_count` 个 WU，等待用户确认后继续
  - **`blocked_on_deps`**：检查 `_blocked_wus`，处理依赖阻塞（回 PLAN_STEP 或等待依赖完成）
  - **`milestone_complete`**：当前 milestone 完成。检查是否有下一个 milestone → SELECT_MILESTONE 或 COMPLETE
- [ ] **禁止**在 `next_action=continue_next_wu` 时停下来——这是与 block guard 同级的硬门禁
- [ ] 如果连续执行了 6 个 WU（`_session_wu_count >= 6`），rotate guard 会触发——这是正常的上下文保护

## 允许的工具

READ_CONTEXT 是纯观察状态，但观察不等于「只能看固定文件」：

| 类别 | 允许？ | 说明 |
|------|--------|------|
| `read`（read_file, grep, glob, git status/log/diff） | ✅ ALLOW | 核心观察工具 |
| `read_exec`（只读 bash：ls, cat, npm/pip list, node -v 等） | ✅ ALLOW | 用于勘察项目现状（依赖安装状态、文件是否存在等） |
| `skill_user`（用户显式 /skill 调用） | ✅ ALLOW | 用户主动输入的命令，不拦截 |
| `skill_auto`（模型自动搜索/匹配 skill） | 🚫 MUST NOT | 属于解空间思维，应在 PLAN_STEP 进行 |
| `code_write` | 🚫 MUST NOT | 改代码不是观察 |
| `exec`（变更 bash：npm install, pytest, build 等） | 🚫 MUST NOT | 有副作用，不在 READ_CONTEXT 做 |
| `doc_write` | 🚫 MUST NOT | 写文档不是观察 |

### 为什么 skill_auto 被挡？

「看到项目结构 → 自动搜匹配的 skill」本质是**解空间思维**——你还没读完上下文就开始想用什么工具解决。正确的流程是：先完成 READ_CONTEXT 收集全貌 → 推进到 PLAN_STEP → 在规划时匹配合适的技能。

## 规则意图（MoE 按需查阅）

被 hook 挡住时，deny 消息中的 ruleId 指向 。
Read 该文件可理解这条规则要防止什么具体危害、为什么存在、正确路径是什么。

理解意图后：遵守规则继续 → 或判断规则在当下不合理 → 触发 revolution 弹窗。

## 退出条件

能回答以下问题才算完成：

- [ ] 当前是哪个 milestone？状态是什么？
- [ ] 当前是哪个 work unit？状态是什么？
- [ ] 硬约束有哪些？（语言/框架/部署/合规）
- [ ] 本轮的非目标是什么？（不能碰的边界）
- [ ] 已知问题有哪些？（Documentation.md §5）
- [ ] 上次做到哪了？下一步是什么？
- [ ] 如果是新会话恢复：最近 10 条状态转移记录显示什么路径？

### 旋转恢复（必须，不可跳过）

如果 `.deepship/continuation.md` 存在且 `state.json` 中 `_rotation_pending = true`：

- [ ] **必须读取** `.deepship/continuation.md`
- [ ] 必须在回复中引用 continuation.md 的 `next_steps`
- [ ] 确认已理解"我在哪 / 已完成 / diff 意图 / 下一步"
- [ ] 确认后，执行自动恢复（清除旋转标记 + 声明 session ownership）：
  ```bash
  python adapters/cc/transition_state.py --auto-recover
  ```
- [ ] 直到 `_rotation_pending` 清除后才能 `transition_state.py --to EXECUTE`
- [ ] 旧 `continuation.md` 可以在 RECORD 后删除

## 突触检测

- [ ] 若 `Skill(architect-mentor)` 可用且 `/mentor` 未显式关闭 → 激活教学覆盖层
