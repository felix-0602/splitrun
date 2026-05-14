"""A2AHandoff — Agent-to-Agent handoff payload 构建与验证."""

from __future__ import annotations

import json
from pathlib import Path

from adapters.interrupt.schemas import A2AHandoffPayload


class A2AHandoff:
    """A2A handoff payload 的构建器/验证器。"""

    REQUIRED_FIELDS = [
        "original_input",
        "normalized_intent_summary",
        "lane_summary",
        "plan_summary",
    ]

    @staticmethod
    def build(
        original_input: str,
        intent_summary: str,
        lane_summary: str,
        plan_summary: str,
        constraints: tuple[str, ...] = (),
        expected_output: str = "",
        should_not_do: tuple[str, ...] = (),
        delegated_wu_id: str = "",
    ) -> A2AHandoffPayload:
        """构建一个 handoff payload。"""
        return A2AHandoffPayload(
            original_input=original_input,
            normalized_intent_summary=intent_summary,
            lane_summary=lane_summary,
            plan_summary=plan_summary,
            constraints=constraints,
            expected_output=expected_output,
            should_not_do=should_not_do,
            delegated_wu_id=delegated_wu_id,
        )

    @staticmethod
    def validate(payload: A2AHandoffPayload) -> tuple[bool, str]:
        """验证 payload 是否完整。返回 (valid, reason)。"""
        data = payload.to_dict()
        missing = [f for f in A2AHandoff.REQUIRED_FIELDS if not data.get(f)]
        if missing:
            return False, f"Missing required fields: {missing}"
        return True, "valid"

    @staticmethod
    def save(payload: A2AHandoffPayload, project_root: str | Path) -> Path:
        """将 handoff payload 持久化到 .deepship/a2a/<wu_id>.json。"""
        root = Path(project_root)
        a2a_dir = root / ".deepship" / "a2a"
        a2a_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{payload.delegated_wu_id or 'handoff'}.json"
        path = a2a_dir / filename
        path.write_text(
            json.dumps(payload.to_dict(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return path

    @staticmethod
    def load(filepath: str | Path) -> A2AHandoffPayload | None:
        """从文件加载 handoff payload。"""
        try:
            data = json.loads(Path(filepath).read_text(encoding="utf-8"))
            return A2AHandoffPayload.from_dict(data)
        except (json.JSONDecodeError, OSError, KeyError):
            return None
