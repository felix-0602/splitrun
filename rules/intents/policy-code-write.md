# policy/code-write: 代码写入门禁

**防止什么危害**：没有计划、没有勘察上下文就直接写代码。

**为什么存在**：DEEPSHIP 的核心纪律是"先理解现状，再规划，再执行"。code_write 只在 EXECUTE 和 REPAIR 两个"执行态"开放——这意味着你必须先经过 READ_CONTEXT、MAP_REALITY、PLAN_STEP 才能写代码。读上下文和写代码是分离的两个阶段。

**不遵守的后果**：模型读了两眼文件就开始改，改了 A 才发现 B 也有关联，越改越多，最后忘了最初要做什么。

**允许的状态**：EXECUTE, REPAIR
**禁止的状态**：所有其他状态
