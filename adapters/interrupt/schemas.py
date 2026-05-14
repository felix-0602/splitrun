"""DEEPSHIP Interrupt Routing Layer — 数据结构."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class RouteType(Enum):
    CACHE_ANSWER = "CACHE_ANSWER"
    SMALL_CONTEXT_TASK = "SMALL_CONTEXT_TASK"
    NEW_LANE_LONG_TASK = "NEW_LANE_LONG_TASK"
    MODIFY_CURRENT_PLAN = "MODIFY_CURRENT_PLAN"


class ReconciliationOutcome(Enum):
    CONTINUE = "continue"
    PAUSE = "pause"
    SUPERSEDED = "superseded"
    PLAN_UPDATED = "plan_updated"
    DELEGATED = "delegated"


@dataclass(frozen=True)
class InterruptContext:
    current_state: str
    current_milestone: str = ""
    current_lane: str | None = None
    current_work_unit: str | None = None
    lane_status: str | None = None
    lane_wu_counts: dict[str, int] = field(default_factory=dict)
    interrupted_at: str = ""

    def __post_init__(self):
        if not self.interrupted_at:
            object.__setattr__(self, "interrupted_at", datetime.now(timezone.utc).isoformat())


@dataclass(frozen=True)
class NormalizedIntent:
    raw_input: str
    summary: str
    route_type: RouteType
    confidence: float = 1.0
    ambiguity: str | None = None
    keywords: tuple[str, ...] = ()
    estimated_complexity: str = "small"
    replaces_current_goal: bool = False
    supplements_current_goal: bool = False


@dataclass(frozen=True)
class A2AHandoffPayload:
    original_input: str
    normalized_intent_summary: str
    lane_summary: str
    plan_summary: str
    constraints: tuple[str, ...] = ()
    expected_output: str = ""
    should_not_do: tuple[str, ...] = ()
    delegated_wu_id: str = ""
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            object.__setattr__(self, "created_at", datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "original_input": self.original_input,
            "normalized_intent_summary": self.normalized_intent_summary,
            "lane_summary": self.lane_summary,
            "plan_summary": self.plan_summary,
            "constraints": list(self.constraints),
            "expected_output": self.expected_output,
            "should_not_do": list(self.should_not_do),
            "delegated_wu_id": self.delegated_wu_id,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> A2AHandoffPayload:
        return cls(
            original_input=data.get("original_input", ""),
            normalized_intent_summary=data.get("normalized_intent_summary", ""),
            lane_summary=data.get("lane_summary", ""),
            plan_summary=data.get("plan_summary", ""),
            constraints=tuple(data.get("constraints", [])),
            expected_output=data.get("expected_output", ""),
            should_not_do=tuple(data.get("should_not_do", [])),
            delegated_wu_id=data.get("delegated_wu_id", ""),
            created_at=data.get("created_at", ""),
        )


@dataclass(frozen=True)
class RouteDecision:
    route_type: RouteType
    should_pause_lane: bool
    summary: str
    handoff_payload: A2AHandoffPayload | None = None
    new_lane_name: str | None = None
    plan_amendment: str | None = None
    clarification_question: str | None = None


@dataclass(frozen=True)
class ReconciliationResult:
    outcome: ReconciliationOutcome
    previous_lane: str | None
    previous_state: str
    summary: str
    updated_lane_state: dict | None = None
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            object.__setattr__(self, "timestamp", datetime.now(timezone.utc).isoformat())
