"""InterruptRouter — 纯函数：根据归一化意图做路由决策."""

from __future__ import annotations

from adapters.interrupt.schemas import (
    InterruptContext,
    NormalizedIntent,
    RouteDecision,
    RouteType,
)


def route(
    intent: NormalizedIntent,
    context: InterruptContext,
) -> RouteDecision:
    """根据归一化意图和中断上下文，生成路由决策。

    纯函数 — 无副作用，可独立测试。
    """
    rt = intent.route_type

    if rt == RouteType.CACHE_ANSWER:
        return RouteDecision(
            route_type=RouteType.CACHE_ANSWER,
            should_pause_lane=False,
            summary="Direct answer from current context — no lane pause needed",
        )

    if rt == RouteType.SMALL_CONTEXT_TASK:
        return RouteDecision(
            route_type=RouteType.SMALL_CONTEXT_TASK,
            should_pause_lane=True,
            summary=f"Delegate to mate/child: {intent.summary}",
            handoff_payload=_build_small_task_handoff(intent, context),
        )

    if rt == RouteType.NEW_LANE_LONG_TASK:
        lane_name = _derive_lane_name(intent)
        return RouteDecision(
            route_type=RouteType.NEW_LANE_LONG_TASK,
            should_pause_lane=True,
            summary=f"Create new lane '{lane_name}' for: {intent.summary}",
            new_lane_name=lane_name,
            handoff_payload=_build_new_lane_handoff(intent, context, lane_name),
        )

    if rt == RouteType.MODIFY_CURRENT_PLAN:
        return RouteDecision(
            route_type=RouteType.MODIFY_CURRENT_PLAN,
            should_pause_lane=True,
            summary=f"Amend current lane plan: {intent.summary}",
            plan_amendment=intent.raw_input,
        )

    # 不可能到达（所有 RouteType 已覆盖）
    return RouteDecision(
        route_type=RouteType.CACHE_ANSWER,
        should_pause_lane=False,
        summary="Unrecognized route type — defaulting to direct answer",
        clarification_question="Could you rephrase your request?",
    )


def _build_small_task_handoff(
    intent: NormalizedIntent,
    context: InterruptContext,
) -> "A2AHandoffPayload | None":
    """为 SMALL_CONTEXT_TASK 构建 A2A handoff payload。"""
    from adapters.interrupt.a2a import A2AHandoff

    return A2AHandoff.build(
        original_input=intent.raw_input,
        intent_summary=intent.summary,
        lane_summary=f"Lane '{context.current_lane or 'main'}' in state {context.current_state}, WU {context.current_work_unit or 'none'}",
        plan_summary=f"Milestone: {context.current_milestone or 'none'}",
        constraints=("Do not modify files outside the delegated scope",),
        expected_output="Answer or code change + evidence",
    )


def _build_new_lane_handoff(
    intent: NormalizedIntent,
    context: InterruptContext,
    lane_name: str,
) -> "A2AHandoffPayload | None":
    """为 NEW_LANE_LONG_TASK 构建 A2A handoff payload。"""
    from adapters.interrupt.a2a import A2AHandoff

    return A2AHandoff.build(
        original_input=intent.raw_input,
        intent_summary=intent.summary,
        lane_summary=f"Parent lane '{context.current_lane or 'main'}', state {context.current_state}",
        plan_summary=f"New lane '{lane_name}' for independent execution",
        constraints=(
            "Create an isolated lane with its own plan and WUs",
            "Do not modify the parent lane's worktree",
        ),
        expected_output=f"Lane '{lane_name}' created with Prompt.md describing the goal",
    )


def _derive_lane_name(intent: NormalizedIntent) -> str:
    """从意图中派生 lane 名称。"""
    import re

    keywords = intent.keywords
    if keywords:
        name = "-".join(keywords[:3])
        name = re.sub(r"[^a-z0-9-]", "", name.lower())
        name = name.strip("-")[:40]
        if name:
            return name
    return f"task-{_short_hash(intent.raw_input)}"


def _short_hash(text: str) -> str:
    import hashlib
    return hashlib.sha256(text.encode()).hexdigest()[:8]
