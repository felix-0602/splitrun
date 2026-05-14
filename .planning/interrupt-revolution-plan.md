# Interrupt Routing Layer + Revolution Channel

## Context

DEEPSHIP 单线程状态机缺少中断处理能力。用户中途打断时无法暂停当前 lane、归一化需求、路由决策。当合理请求被 DEEPSHIP 自身约束拦住时，没有正式的框架自进化通道。

## 设计原则

- 不新增状态机状态，用 `_interrupt_*` / `_revolution_*` 运行时标记（类比 `_rotation_pending`）
- 路由逻辑为纯函数，可独立测试
- 复用现有 lane、WU、rotate、guard 模式
- 普通执行路径零影响

## 模块结构

```
adapters/interrupt/          # 中断路由层
├── __init__.py              # 公共 API
├── schemas.py               # RouteType, InterruptContext, NormalizedIntent, RouteDecision, A2AHandoffPayload, ReconciliationResult
├── detector.py              # InterruptDetector — 检测活跃 lane
├── classifier.py            # IntentClassifier — 归一化 + 4 路分类 + 澄清
├── router.py                # InterruptRouter — 纯函数路由
├── a2a.py                   # A2AHandoff — handoff payload 构建/验证
└── reconciler.py            # Reconciler — 5 种协调结果应用

adapters/revolution/         # 革命通道
├── __init__.py
├── schemas.py               # RevolutionProposal, BlockingConstraint, ProposedChange, RollbackPlan
├── detector.py              # RevolutionDetector — 识别合理请求被框架拦住
├── proposal.py              # RevolutionProposalBuilder — 无副作用
├── evolution_lane.py        # 批准后创建 self-evolution lane
└── audit.py                 # 审计日志
```

## 状态机集成

用 state.json `_` 前缀运行时标记，不新增状态：
- `_interrupt_pending`, `_interrupt_type`, `_interrupted_lane`, `_interrupt_intent`
- `_revolution_proposal`, `_revolution_status`, `_revolution_lane`
- transition_state.py 加 `--clear-interrupt` + guard

## 实现顺序

1. ✅ Priority 1: writeKind fix (`.planning/**` → doc_write)
2. ✅ Priority 2: Anti-bypass guard (Bash 写文件受 policy 管)
3. Interrupt schemas + __init__
4. Interrupt core (detector, classifier, router, a2a, reconciler)
5. Revolution schemas + core (detector, proposal, evolution_lane, audit)
6. Integration (transition_state, rules, protocol)
7. Tests + conformance

## 修改文件

新建: adapters/interrupt/* (7), adapters/revolution/* (6), protocol/interrupt.md, protocol/revolution.md, rules/static/interrupt.md, rules/static/revolution.md, tests/conformance/interrupt_cases.json, tests/conformance/revolution_cases.json, tests/test_interrupt_*.py, tests/test_revolution_*.py

修改: adapters/cc/transition_state.py, adapters/parallel/__init__.py, rules/static/loop.md
