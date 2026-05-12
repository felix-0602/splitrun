#!/usr/bin/env python3
"""Initialize a DEEPSHIP runtime directory in a project workspace."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def _initial_state() -> dict:
    return {
        "_schema": "deepship-state/1.0",
        "current_state": "READ_CONTEXT",
        "current_milestone": None,
        "current_work_unit": None,
        "last_completed_state": None,
        "next_action": "enter READ_CONTEXT: read Prompt.md / Plan.md / Documentation.md",
        "validation_status": None,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def _initial_work_units() -> dict:
    return {
        "_schema": "deepship-work-units/1.0",
        "milestone": None,
        "work_units": [],
    }


def init_deepship(project_root: str | Path = ".") -> list[Path]:
    """Create missing .deepship runtime files and return the files created."""
    root = Path(project_root).resolve()
    deepship_dir = root / ".deepship"
    deepship_dir.mkdir(parents=True, exist_ok=True)

    files = {
        deepship_dir / "state.json": json.dumps(_initial_state(), indent=2, ensure_ascii=False) + "\n",
        deepship_dir / "work_units.json": json.dumps(_initial_work_units(), indent=2, ensure_ascii=False) + "\n",
        deepship_dir / "log.jsonl": "",
    }

    created: list[Path] = []
    for path, content in files.items():
        if not path.exists():
            path.write_text(content, encoding="utf-8")
            created.append(path)

    return created


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize .deepship runtime state")
    parser.add_argument("project_root", nargs="?", default=".", help="Project root to initialize")
    args = parser.parse_args()

    created = init_deepship(args.project_root)
    print(json.dumps({"created": [str(path) for path in created]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
