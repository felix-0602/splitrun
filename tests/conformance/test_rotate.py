"""
DEEPSHIP Rotate 一致性测试 — 覆盖 rotate() 核心路径、门禁、拒绝路径。

rotate() 的契约：
  - rotatable WU → 写 continuation.md + 设 _rotation_pending=true
  - inline WU → sys.exit(1)
  - continuation_mode != rotatable → sys.exit(1)
  - 空 diff_intent → sys.exit(1)
  - 空 next_steps → sys.exit(1)
  - _rotation_pending 为 true 时 transition EXECUTE 被拒绝
  - no_spawn → 只写文件，不调 spawn_new_session
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from adapters.cc import transition_state

# TECH DEBT: __init__.py 把 rotate 函数名覆盖了子模块名（Python 已知陷阱：
# from .rotate import rotate 导致 adapters.parallel.rotate 指向函数而非模块）。
# 当前绕过方式：del 包属性 → import 子模块 → 补回包属性。
# 正确修法：__init__.py 把函数改名或放到子属性下（如 rotate.rotate → rotate.run）。
# TODO: 改 __init__.py 导出设计后删除这段。
import adapters.parallel
del adapters.parallel.rotate
import adapters.parallel.rotate as rotate_module
adapters.parallel.rotate = rotate_module.rotate


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _rotatable_wu(**overrides) -> dict:
    wu = {
        "id": "WU-ROT-001",
        "goal": "test rotatable WU",
        "scope": "test",
        "files_allowed": ["src/test.py"],
        "depends_on": [],
        "execution_mode": "serial",
        "continuation_mode": "rotatable",
        "parallel_group": None,
        "acceptance_tests": ["pytest"],
        "risk_level": "low",
        "owner": "orchestrator",
        "status": "in_progress",
    }
    wu.update(overrides)
    return wu


class RotateCoreTest(unittest.TestCase):
    """rotate() 核心路径测试。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.deepship_dir = self.root / ".deepship"
        self.deepship_dir.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def _init_state(self, wu_id="WU-ROT-001", current_state="EXECUTE"):
        _write_json(self.deepship_dir / "state.json", {
            "current_state": current_state,
            "current_milestone": "test",
            "current_work_unit": wu_id,
        })

    def _init_work_units(self, wus=None):
        if wus is None:
            wus = [_rotatable_wu()]
        _write_json(self.deepship_dir / "work_units.json", {"work_units": wus})

    # ── 正向路径 ────────────────────────────────────────

    def test_rotatable_wu_writes_continuation_and_sets_rotation_pending(self):
        """rotatable WU + 有效参数 → continuation.md 写入 + _rotation_pending=true"""
        self._init_state()
        self._init_work_units()

        cont_path = rotate_module.rotate(
            project_root=self.root,
            diff_intent="重构了 auth 模块",
            next_steps="1. pytest tests/\n2. VALIDATE",
            no_spawn=True,
        )

        self.assertIsNotNone(cont_path)
        self.assertTrue(cont_path.exists(), f"continuation.md 应存在: {cont_path}")

        content = cont_path.read_text(encoding="utf-8")
        self.assertIn("重构了 auth 模块", content)
        self.assertIn("pytest tests/", content)

        state = json.loads((self.deepship_dir / "state.json").read_text(encoding="utf-8"))
        self.assertTrue(state.get("_rotation_pending"), "_rotation_pending 应为 true")
        self.assertIn("_rotated_at", state)
        self.assertEqual(state["_rotated_from_wu"], "WU-ROT-001")

    def test_rotatable_wu_completes_history_section(self):
        """continuation.md 包含已完成 WU 列表。"""
        self._init_state()
        self._init_work_units([_rotatable_wu(), {
            "id": "WU-DONE-001",
            "goal": "already done",
            "scope": "done",
            "files_allowed": ["src/done.py"],
            "depends_on": [],
            "execution_mode": "inline",
            "continuation_mode": "normal",
            "parallel_group": None,
            "acceptance_tests": [],
            "risk_level": "low",
            "owner": "orchestrator",
            "status": "done",
        }])

        cont_path = rotate_module.rotate(
            project_root=self.root,
            diff_intent="改动 X",
            next_steps="Y",
            no_spawn=True,
        )

        content = cont_path.read_text(encoding="utf-8")
        self.assertIn("WU-DONE-001", content)

    # ── 拒绝路径 — execution_mode ─────────────────────────

    def test_rejects_inline_wu(self):
        """execution_mode=inline → sys.exit(1)"""
        self._init_state()
        self._init_work_units([_rotatable_wu(execution_mode="inline")])

        with self.assertRaises(SystemExit) as ctx:
            rotate_module.rotate(
                project_root=self.root,
                diff_intent="改动",
                next_steps="步骤",
                no_spawn=True,
            )
        self.assertEqual(ctx.exception.code, 1)

    # ── 拒绝路径 — continuation_mode ──────────────────────

    def test_rejects_non_rotatable_continuation_mode(self):
        """continuation_mode=normal → sys.exit(1)"""
        self._init_state()
        self._init_work_units([_rotatable_wu(continuation_mode="normal")])

        with self.assertRaises(SystemExit) as ctx:
            rotate_module.rotate(
                project_root=self.root,
                diff_intent="改动",
                next_steps="步骤",
                no_spawn=True,
            )
        self.assertEqual(ctx.exception.code, 1)

    # ── 拒绝路径 — 空参数 ─────────────────────────────────

    def test_rejects_empty_diff_intent(self):
        """diff_intent 为空或默认值 → sys.exit(1)"""
        self._init_state()
        self._init_work_units()

        with self.assertRaises(SystemExit) as ctx:
            rotate_module.rotate(
                project_root=self.root,
                diff_intent="",
                next_steps="valid step",
                no_spawn=True,
            )
        self.assertEqual(ctx.exception.code, 1)

    def test_rejects_default_diff_intent(self):
        """diff_intent 为默认占位符 → sys.exit(1)"""
        self._init_state()
        self._init_work_units()

        with self.assertRaises(SystemExit) as ctx:
            rotate_module.rotate(
                project_root=self.root,
                diff_intent="（见 git diff）",
                next_steps="valid step",
                no_spawn=True,
            )
        self.assertEqual(ctx.exception.code, 1)

    def test_rejects_empty_next_steps(self):
        """next_steps 为空或默认值 → sys.exit(1)"""
        self._init_state()
        self._init_work_units()

        with self.assertRaises(SystemExit) as ctx:
            rotate_module.rotate(
                project_root=self.root,
                diff_intent="valid intent",
                next_steps="",
                no_spawn=True,
            )
        self.assertEqual(ctx.exception.code, 1)

    # ── no_spawn ────────────────────────────────────────

    def test_no_spawn_does_not_call_spawn_new_session(self):
        """no_spawn=True → 写 continuation.md，不调 spawn_new_session"""
        self._init_state()
        self._init_work_units()

        with patch.object(rotate_module, "spawn_new_session") as mock_spawn:
            cont_path = rotate_module.rotate(
                project_root=self.root,
                diff_intent="改动",
                next_steps="步骤",
                no_spawn=True,
            )
            mock_spawn.assert_not_called()

        self.assertTrue(cont_path.exists())


class RotateTransitionGateTest(unittest.TestCase):
    """transition_state 的 _rotation_pending 门禁测试。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.deepship_dir = self.root / ".deepship"
        self.deepship_dir.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def _init_state(self, **overrides):
        data = {
            "current_state": "READ_CONTEXT",
            "current_milestone": "test",
            "current_work_unit": "WU-ROT-001",
        }
        data.update(overrides)
        _write_json(self.deepship_dir / "state.json", data)

    def _init_work_units(self):
        _write_json(self.deepship_dir / "work_units.json", {
            "work_units": [_rotatable_wu()],
        })

    def test_rotation_pending_blocks_execute(self):
        """_rotation_pending=true 时 transition EXECUTE 被拒绝"""
        self._init_state(
            current_state="READ_CONTEXT",
            _rotation_pending=True,
            _rotated_at="2026-05-12T14:00:00Z",
            _rotated_from_wu="WU-ROT-001",
        )
        self._init_work_units()

        result = transition_state.transition(
            to_state="EXECUTE",
            wu_id="WU-ROT-001",
            project_root=self.root,
        )
        self.assertFalse(result["success"], f"应拒绝: {result}")
        self.assertIn("rotation_pending", result["reason"].lower())

    def test_no_rotation_pending_allows_execute(self):
        """无 _rotation_pending 时 transition EXECUTE 正常"""
        self._init_state(current_state="PLAN_STEP")
        self._init_work_units()

        result = transition_state.transition(
            to_state="EXECUTE",
            wu_id="WU-ROT-001",
            project_root=self.root,
        )
        self.assertTrue(result["success"], f"应允许: {result}")

    # ── clear_rotation 门禁 ──────────────────────────

    def test_clear_rotation_allowed_in_read_context(self):
        """--clear-rotation 在 READ_CONTEXT 状态下成功清除标记"""
        self._init_state(
            current_state="READ_CONTEXT",
            _rotation_pending=True,
            _rotated_at="2026-05-12T14:00:00Z",
            _rotated_from_wu="WU-ROT-001",
        )
        self._init_work_units()

        result = transition_state.transition(
            to_state="READ_CONTEXT",
            project_root=self.root,
            clear_rotation=True,
        )
        self.assertTrue(result["success"], f"应允许: {result}")

        state = json.loads((self.deepship_dir / "state.json").read_text(encoding="utf-8"))
        self.assertNotIn("_rotation_pending", state)
        self.assertNotIn("_rotated_at", state)
        self.assertNotIn("_rotated_from_wu", state)

    def test_clear_rotation_rejected_in_execute(self):
        """--clear-rotation 在 EXECUTE 状态下被拒绝"""
        self._init_state(
            current_state="EXECUTE",
            _rotation_pending=True,
        )
        self._init_work_units()

        result = transition_state.transition(
            to_state="EXECUTE",
            project_root=self.root,
            clear_rotation=True,
        )
        self.assertFalse(result["success"], f"应拒绝: {result}")
        self.assertIn("READ_CONTEXT", result["reason"])


if __name__ == "__main__":
    unittest.main()
