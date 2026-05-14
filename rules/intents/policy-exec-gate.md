# policy/exec-gate: 破坏性 Bash 门禁

**防止什么危害**：在只读状态（READ_CONTEXT、MAP_REALITY）下执行有副作用的命令。

**为什么存在**：READ_CONTEXT 和 MAP_REALITY 是"勘察"状态——你应该收集信息，不应该改变环境。pytest、npm install、git push 都有副作用，应该等到 EXECUTE 再做。

**不遵守的后果**：
- 勘察中途跑了测试 → 测试失败但你还不知道代码长什么样，浪费时间去 debug
- 勘察中途装了依赖 → 依赖冲突但你还没理解项目结构
- PLAN_STEP 中途跑了 migration → 数据被改了但计划还没写好

**允许的状态**：EXECUTE, VALIDATE, REPAIR
**禁止的状态**：READ_CONTEXT, CLARIFY_INTENT, MAP_REALITY, SELECT_MILESTONE, PLAN_STEP, RECORD, ADVANCE, BLOCK, COMPLETE

**例外**：DEEPSHIP 框架自身的管理命令（transition_state.py, rotate.py, verify.py 等）始终允许。
