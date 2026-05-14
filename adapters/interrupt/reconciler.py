"""Reconciler — 中断处理完成后，协调当前 lane 状态."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from adapters.interrupt.schemas import ReconciliationOutcome, ReconciliationResult


def reconcile(
    outcome: ReconciliationOutcome,
    previous_lane: str | None,
    previous_state: str,
    project_root: str | Path,
    summary: str = "",
) -> ReconciliationResult:
    """应用协调结果到 DEEPSHIP 状态。

    根据 outcome 类型，更新 state.json 中的中断标记。
    返回 ReconciliationResult。
    """
    root = Path(project_root)
    state_path = root / ".deepship" / "state.json"

    if not state_path.exists():
        return ReconciliationResult(
            outcome=outcome,
            previous_lane=previous_lane,
            previous_state=previous_state,
            summary="state.json not found — reconciliation skipped",
        )

    state = json.loads(state_path.read_text(encoding="utf-8"))

    updates: dict[str, str | None] = {}
    if outcome == ReconciliationOutcome.CONTINUE:
        updates = {
            "_interrupt_pending": False,
            "_interrupt_handled_at": datetime.now(timezone.utc).isoformat(),
            "_interrupt_reconciliation": "continue",
        }
    elif outcome == ReconciliationOutcome.PAUSE:
        updates = {
            "_interrupt_pending": True,
            "_interrupt_reconciliation": "pause",
        }
    elif outcome == ReconciliationOutcome.SUPERSEDED:
        updates = {
            "_interrupt_pending": False,
            "_interrupt_handled_at": datetime.now(timezone.utc).isoformat(),
            "_interrupt_reconciliation": "superseded",
        }
    elif outcome == ReconciliationOutcome.PLAN_UPDATED:
        updates = {
            "_interrupt_pending": False,
            "_interrupt_handled_at": datetime.now(timezone.utc).isoformat(),
            "_interrupt_reconciliation": "plan_updated",
        }
    elif outcome == ReconciliationOutcome.DELEGATED:
        updates = {
            "_interrupt_pending": True,
            "_interrupt_reconciliation": "delegated",
        }

    for key, value in updates.items():
        state[key] = value

    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    state_path.write_text(
        json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8",
    )

    return ReconciliationResult(
        outcome=outcome,
        previous_lane=previous_lane,
        previous_state=previous_state,
        summary=summary or f"Reconciled: {outcome.value}",
    )


def clear_interrupt(project_root: str | Path) -> ReconciliationResult:
    """清除所有中断标记，恢复正常执行。

    类比 transition_state.py --clear-rotation。
    """
    root = Path(project_root)
    state_path = root / ".deepship" / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))

    interrupt_keys = [
        "_interrupt_pending",
        "_interrupt_type",
        "_interrupt_received_at",
        "_interrupted_lane",
        "_interrupt_intent",
        "_interrupt_handled_at",
        "_interrupt_reconciliation",
    ]
    for key in interrupt_keys:
        state.pop(key, None)

    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    state_path.write_text(
        json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8",
    )

    return ReconciliationResult(
        outcome=ReconciliationOutcome.CONTINUE,
        previous_lane=state.get("current_work_unit", ""),
        previous_state=state.get("current_state", ""),
        summary="Interrupt flags cleared — normal execution resumed",
    )
