# GitHub Profile Copy

This file contains copy that can be pasted into GitHub repository settings, release notes, or social posts.

## Repository Description

AI 工程执行协议 — 状态机 + Work Unit + Intent-Aware Profiles + Fork/Rotate 两轴执行模型。v2.3

## Topics

```text
ai-engineering
state-machine
autonomous-agent
workflow-engine
claude-code
conformance-testing
parallel-execution
context-management
```

## Short English Intro

DEEPSHIP is a recoverable execution discipline for AI coding agents. v2.3 adds Intent-Aware Profiles that adapt state machine strictness to user intent (development/deployment/debug/skill/learning), plus lane coordination for isolated parallel work with file conflict detection.

## Short Chinese Intro

DEEPSHIP 是一套 AI 工程执行纪律。v2.3 引入 Intent-Aware Profiles——根据用户意图信号（开发/部署/调试/技能/学习）自适应调整状态机严格度，不再所有场景走同一套 11 状态链。加上 lane 并行隔离、自动续推、revolution 越界令牌。

## Long Chinese Intro

AI 编程代理的问题通常不是"不会写代码"，而是长时间工作时会散：忘记计划、越界改文件、子会话无法验收、上下文耗尽后失忆、prompt 规则没有执行点。更根本的问题是：**所有场景走同一套严格规则——部署也要勘察代码库，调试也要澄清意图。**

DEEPSHIP 给这些问题加了一套工程纪律：

- 用 **Intent-Aware Profiles** 根据用户意图自适应——deployment 直通部署，debug 保留 Reality-First 跳过规划，skill/learning 绕过状态机全放行
- 用**状态机**定义当前处在读上下文、规划、执行、验证还是记录
- 用 **Work Unit** 给每块任务定义 goal、scope、files_allowed 和 acceptance_tests
- 用 `.deepship/` 文件保存现场，让新会话可以恢复
- 用 **fork/worktree** 支持已规划任务的并行执行
- 用 **rotate/checkpoint** 支持长任务跨会话继续（counter ≥6 或上下文 ≤25% 硬触发）
- 用 **lane** 创建隔离并行通道，文件冲突自动检测
- 用 **revolution** 令牌给用户批准的临时越界开权限
- 用 **自动续推** 在 ADVANCE 后自动推进到下一个 WU（block 纪律级别）
- 用 **collector** 回收子会话结果，检查边界、测试和冲突
- 用 **conformance cases** 让不同 runtime 证明自己真的实现了这套纪律

DEEPSHIP 不是无限自治 prompt，也不是单纯自动化脚本。它更像是给 AI coding agent 的施工纪律：每一步都要有边界、证据和回收路径。

## One-Liners

- Give AI coding agents discipline, not just prompts.
- Turn "the agent says it is done" into "the system accepted it."
- Recoverable, auditable, bounded execution for AI engineering agents.
- Intent-Aware Profiles: adapt rule strictness to what you're actually doing.
- 给 AI 编程代理加纪律，而不是继续堆 prompt。
- 让"模型说做完了"变成"系统验收通过了"。
- 部署、调试、学习——不同意图，不同规则严格度。

## Social Post Draft

DEEPSHIP v2.3 发布了。核心洞察：AI agent 不需要更多 prompt 规则——它需要**根据意图自适应**的规则。

v2.3 引入 Intent-Aware Profiles：5 个 profile 根据用户意图信号自动调整状态机严格度。
- development：完整 11 状态链路
- deployment：4 状态快速部署（跳过勘察/规划/验证）
- debug：6 状态（保留 Reality-First，跳过规划）
- skill/learning：绕过状态机，全放行

加上 lane 并行隔离（文件冲突自动检测）、自动续推（ADVANCE 后零等待推进到下一个 WU）、revolution 令牌（用户批准的临时越界）。

核心理念没变：把长任务拆成可恢复、可检查、可拒绝、可集成的 Work Unit。变的是——规则不再死板，它知道你在干什么。
