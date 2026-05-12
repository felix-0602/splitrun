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

## 退出条件

能回答以下问题才算完成：

- [ ] 当前是哪个 milestone？状态是什么？
- [ ] 当前是哪个 work unit？状态是什么？
- [ ] 硬约束有哪些？（语言/框架/部署/合规）
- [ ] 本轮的非目标是什么？（不能碰的边界）
- [ ] 已知问题有哪些？（Documentation.md §5）
- [ ] 上次做到哪了？下一步是什么？
- [ ] 如果是新会话恢复：最近 10 条状态转移记录显示什么路径？

## 突触检测

- [ ] 若 `Skill(architect-mentor)` 可用且 `/mentor` 未显式关闭 → 激活教学覆盖层
