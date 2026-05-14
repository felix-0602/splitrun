#!/usr/bin/env python3
"""DEEPSHIP 项目的 Claude Code 状态栏渲染器。"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


DEFAULT_COLUMNS = 120
MIN_COLUMNS = 20


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _find_project_root(start: str | Path | None) -> Path | None:
    if not start:
        return None
    current = Path(start).resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        if (candidate / ".deepship" / "state.json").exists() or (
            candidate / ".deepship" / "work_units.json"
        ).exists():
            return candidate
    return None


def _safe_text(value: Any, fallback: str = "-") -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return text if text else fallback


def _current_work_unit(work_units: list[dict[str, Any]], wu_id: str) -> dict[str, Any]:
    for unit in work_units:
        if unit.get("id") == wu_id:
            return unit
    return {}


def _work_unit_progress(work_units: list[dict[str, Any]]) -> str:
    total = len(work_units)
    if total == 0:
        return "0/0 WU"
    integrated = sum(1 for unit in work_units if unit.get("status") == "integrated")
    return f"{integrated}/{total} integrated"


def _context_percent(payload: dict[str, Any]) -> str | None:
    context = payload.get("context_window")
    if not isinstance(context, dict):
        return None
    pct = context.get("used_percentage")
    if pct is None:
        return None
    try:
        return f"ctx {int(float(pct))}%"
    except (TypeError, ValueError):
        return None


def _truncate(text: str, columns: int) -> str:
    width = max(MIN_COLUMNS, columns)
    if len(text) <= width:
        return text
    if width <= 3:
        return "." * width
    return text[: width - 3].rstrip() + "..."


def render(payload: dict[str, Any]) -> str:
    """Render a single statusLine row from Claude Code stdin payload."""
    root = _find_project_root(payload.get("cwd") or payload.get("workspace", {}).get("current_dir"))
    if root is None:
        return ""

    state = _read_json(root / ".deepship" / "state.json")
    work_unit_data = _read_json(root / ".deepship" / "work_units.json")
    units_raw = work_unit_data.get("work_units", [])
    work_units = [unit for unit in units_raw if isinstance(unit, dict)] if isinstance(units_raw, list) else []

    current_state = _safe_text(state.get("current_state"), "NO_STATE")
    milestone = _safe_text(state.get("current_milestone") or work_unit_data.get("milestone"))
    wu_id = _safe_text(state.get("current_work_unit"))
    current_wu = _current_work_unit(work_units, wu_id)
    wu_status = _safe_text(current_wu.get("status"), "no-wu")

    parts = [
        f"DEEPSHIP {current_state}",
        milestone,
        f"{wu_id}:{wu_status}",
        _work_unit_progress(work_units),
    ]
    context = _context_percent(payload)
    if context:
        parts.append(context)

    try:
        columns = int(payload.get("columns") or DEFAULT_COLUMNS)
    except (TypeError, ValueError):
        columns = DEFAULT_COLUMNS

    return _truncate(" | ".join(parts), columns)


def main() -> None:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        payload = {}
    sys.stdout.write(render(payload))


if __name__ == "__main__":
    main()
