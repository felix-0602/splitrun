"""
Lane index schema contract tests — 强制 verify.py 要求的字段契约。

verify.py line 65: 每个 lane entry 必须包含
status, task, worktree, files_claimed, spawned_at
"""

import unittest
from adapters.gates import validate_lane_index_entry, LANE_INDEX_REQUIRED_FIELDS


class LaneIndexSchemaTest(unittest.TestCase):
    """lane index entry schema 契约 —— 少任何字段都是硬错误。"""

    def test_valid_entry_passes(self):
        """完整 entry 不报缺失字段。"""
        entry = {
            "status": "active",
            "task": "fix auth bug",
            "worktree": "/tmp/worktrees/LANE-001",
            "files_claimed": ["src/auth.py"],
            "spawned_at": "2026-05-17T10:00:00Z",
        }
        self.assertEqual(validate_lane_index_entry(entry), [])

    def test_missing_worktree_is_detected(self):
        """缺少 worktree 字段必须被检出（dispatch 旧版问题）。"""
        entry = {
            "status": "active",
            "task": "fix auth bug",
            "files_claimed": ["src/auth.py"],
            "spawned_at": "2026-05-17T10:00:00Z",
        }
        missing = validate_lane_index_entry(entry)
        self.assertIn("worktree", missing)

    def test_missing_spawned_at_is_detected(self):
        entry = {
            "status": "active",
            "task": "fix auth bug",
            "worktree": "/tmp/LANE-001",
            "files_claimed": ["src/auth.py"],
        }
        missing = validate_lane_index_entry(entry)
        self.assertIn("spawned_at", missing)

    def test_missing_files_claimed_is_detected(self):
        entry = {
            "status": "active",
            "task": "fix auth bug",
            "worktree": "/tmp/LANE-001",
            "spawned_at": "2026-05-17T10:00:00Z",
        }
        missing = validate_lane_index_entry(entry)
        self.assertIn("files_claimed", missing)

    def test_empty_entry_fails_all(self):
        """空 entry 应该列出全部 5 个必填字段。"""
        missing = validate_lane_index_entry({})
        self.assertEqual(len(missing), len(LANE_INDEX_REQUIRED_FIELDS))

    def test_required_fields_set_is_stable(self):
        """必填字段集合不应意外变化 —— 修改需同步更新 verify.py 和 spawn_lane.register_lane。"""
        self.assertEqual(
            set(LANE_INDEX_REQUIRED_FIELDS),
            {"status", "task", "worktree", "files_claimed", "spawned_at"},
        )


if __name__ == "__main__":
    unittest.main()
