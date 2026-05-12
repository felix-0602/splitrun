# GitHub Profile Copy

This file contains copy that can be pasted into GitHub repository settings, release notes, or social posts.

## Repository Description

Recoverable execution discipline for AI coding agents: Work Units, state machine, fork/rotate sessions, policy gates, and conformance tests.

## Topics

```text
ai-agents
coding-agents
claude-code
agent-runtime
workflow
state-machine
worktree
developer-tools
ai-engineering
```

## Short English Intro

DEEPSHIP is a recoverable execution discipline for AI coding agents. It turns long-running AI development work into bounded Work Units with explicit file boundaries, validation evidence, state persistence, forked worker sessions, and conformance tests.

## Short Chinese Intro

DEEPSHIP 是一套 AI 工程执行纪律。它把长任务拆成可恢复、可检查、可拒绝、可集成的 Work Unit，用状态机、文件边界、fork/rotate 会话和 conformance 测试约束 AI 编程代理。

## Long Chinese Intro

AI 编程代理的问题通常不是“不会写代码”，而是长时间工作时会散：忘记计划、越界改文件、子会话无法验收、上下文耗尽后失忆、prompt 规则没有执行点。

DEEPSHIP 给这些问题加了一套工程纪律：

- 用状态机定义当前处在读上下文、规划、执行、验证还是记录
- 用 Work Unit 给每块任务定义 goal、scope、files_allowed 和 acceptance_tests
- 用 `.deepship/` 文件保存现场，让新会话可以恢复
- 用 fork/worktree 支持已规划任务的并行执行
- 用 rotate/checkpoint 支持长任务跨会话继续
- 用 collector 回收子会话结果，检查边界、测试和冲突
- 用 conformance cases 让不同 runtime 证明自己真的实现了这套纪律

DEEPSHIP 不是无限自治 prompt，也不是单纯自动化脚本。它更像是给 AI coding agent 的施工纪律：每一步都要有边界、证据和回收路径。

## One-Liners

- Give AI coding agents discipline, not just prompts.
- Turn “the agent says it is done” into “the system accepted it.”
- Recoverable, auditable, bounded execution for AI engineering agents.
- 给 AI 编程代理加纪律，而不是继续堆 prompt。
- 让“模型说做完了”变成“系统验收通过了”。

## Social Post Draft

我最近在做 DEEPSHIP：一套给 AI 编程代理用的工程执行纪律。

它不追求“无限自治”，而是解决更现实的问题：AI 长时间写代码时会忘计划、越界改文件、子会话无法验收、上下文耗尽后失忆。

DEEPSHIP 把任务拆成 Work Unit，每个 WU 都有目标、范围、允许修改的文件和验收测试。执行过程由状态机推进，现场写进 `.deepship/`，并行用 fork/worktree，长任务用 rotate/checkpoint，子会话结果由 collector 回收检查。

我现在越来越觉得，AI agent 真正需要的不是更多 prompt，而是一套能恢复、能拒绝、能验收的纪律。
