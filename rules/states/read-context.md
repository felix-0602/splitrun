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
