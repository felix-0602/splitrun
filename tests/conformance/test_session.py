"""
DEEPSHIP Session Ownership 一致性测试。

SessionManager 契约：
  - claim_ownership: 写 session.json，返回 previous_owner
  - is_owner: worktree 匹配 → True；无 session.json → True（兼容）
  - is_stale: 超时 → True；无 session.json → True
  - heartbeat: owner 可更新；非 owner 被拒
  - release_ownership: owner 可释放；非 owner 被拒
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from adapters.session.session import SessionManager


class SessionClaimTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / ".deepship").mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def test_claim_ownership_writes_session_json(self):
        mgr = SessionManager(self.root)
        result = mgr.claim_ownership(str(self.root))
        self.assertTrue(result["success"])
        self.assertIsNone(result["previous_owner"])

        session_path = self.root / ".deepship" / "session.json"
        self.assertTrue(session_path.exists())
        data = json.loads(session_path.read_text(encoding="utf-8"))
        self.assertEqual(data["owner_worktree"], str(self.root.resolve()))
        self.assertIn("owner_started_at", data)
        self.assertIn("last_heartbeat", data)

    def test_claim_ownership_records_previous_owner(self):
        mgr = SessionManager(self.root)
        mgr.claim_ownership(str(self.root))

        # 模拟第二个 worktree claim
        wt2 = self.root / "worktree2"
        wt2.mkdir(parents=True)
        result = mgr.claim_ownership(str(wt2))
        self.assertTrue(result["success"])
        self.assertEqual(result["previous_owner"], str(self.root.resolve()))

    def test_is_owner_true_for_claimed_worktree(self):
        mgr = SessionManager(self.root)
        mgr.claim_ownership(str(self.root))
        self.assertTrue(mgr.is_owner(str(self.root)))

    def test_is_owner_false_for_different_worktree(self):
        mgr = SessionManager(self.root)
        mgr.claim_ownership(str(self.root))
        other = self.root / "other"
        other.mkdir()
        self.assertFalse(mgr.is_owner(str(other)))

    def test_is_owner_true_when_no_session_json(self):
        """向后兼容：无 session.json 时任何 worktree 都是 owner。"""
        mgr = SessionManager(self.root)
        self.assertTrue(mgr.is_owner(str(self.root)))
        self.assertTrue(mgr.is_owner("/some/other/path"))

    def test_is_stale_true_when_no_session_json(self):
        mgr = SessionManager(self.root)
        self.assertTrue(mgr.is_stale(timeout_minutes=30))

    def test_is_stale_false_for_fresh_heartbeat(self):
        mgr = SessionManager(self.root)
        mgr.claim_ownership(str(self.root))
        self.assertFalse(mgr.is_stale(timeout_minutes=120))

    def test_heartbeat_updates_timestamp(self):
        mgr = SessionManager(self.root)
        mgr.claim_ownership(str(self.root))

        old_data = json.loads(
            (self.root / ".deepship" / "session.json").read_text(encoding="utf-8")
        )
        old_hb = old_data["last_heartbeat"]

        import time
        time.sleep(0.01)  # 确保时间戳不同

        result = mgr.heartbeat(str(self.root))
        self.assertTrue(result["success"])

        new_data = json.loads(
            (self.root / ".deepship" / "session.json").read_text(encoding="utf-8")
        )
        self.assertNotEqual(new_data["last_heartbeat"], old_hb)

    def test_heartbeat_rejects_non_owner(self):
        mgr = SessionManager(self.root)
        mgr.claim_ownership(str(self.root))
        other = self.root / "other"
        other.mkdir()
        result = mgr.heartbeat(str(other))
        self.assertFalse(result["success"])

    def test_release_ownership_removes_owner(self):
        mgr = SessionManager(self.root)
        mgr.claim_ownership(str(self.root))
        result = mgr.release_ownership(str(self.root))
        self.assertTrue(result["success"])

        data = json.loads(
            (self.root / ".deepship" / "session.json").read_text(encoding="utf-8")
        )
        self.assertNotIn("owner_worktree", data)
        self.assertIn("released_at", data)

    def test_release_ownership_rejects_non_owner(self):
        mgr = SessionManager(self.root)
        mgr.claim_ownership(str(self.root))
        other = self.root / "other"
        other.mkdir()
        result = mgr.release_ownership(str(other))
        self.assertFalse(result["success"])

    def test_cli_claim_ownership(self):
        script = Path(__file__).resolve().parents[2] / "adapters" / "session" / "session.py"
        result = subprocess.run(
            [
                sys.executable,
                str(script),
                "claim",
                "--project-root",
                str(self.root),
                "--worktree",
                str(self.root),
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads((self.root / ".deepship" / "session.json").read_text(encoding="utf-8"))
        self.assertEqual(data["owner_worktree"], str(self.root.resolve()))


class SessionRotateFlowTest(unittest.TestCase):
    """模拟 rotate 流程：旧 worktree 旋转 → 新 worktree claim → 旧被拒。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / ".deepship").mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_rotate_flow_old_session_blocked(self):
        """同一项目根，新 session claim 后旧 session worktree 不再是 owner。"""
        # 一个 SessionManager 管理同一个 .deepship/session.json
        mgr = SessionManager(self.root)

        # 旧 session 在 lane-a worktree claim
        old_wt = str((self.root / "lane-a").resolve())
        mgr.claim_ownership(old_wt)
        self.assertTrue(mgr.is_owner(old_wt))

        # 新 session 在 lane-b worktree claim（rotate 后）
        new_wt = str((self.root / "lane-b").resolve())
        result = mgr.claim_ownership(new_wt)
        self.assertTrue(result["success"])
        self.assertEqual(result["previous_owner"], old_wt)

        # 新 worktree 是 owner，旧 worktree 不是
        self.assertTrue(mgr.is_owner(new_wt))
        self.assertFalse(mgr.is_owner(old_wt))

    def test_rotate_flow_no_session_json_is_backward_compatible(self):
        """无 session.json 时所有 worktree 都是 owner（向后兼容）。"""
        mgr = SessionManager(self.root)
        self.assertTrue(mgr.is_owner(str(self.root)))
        self.assertTrue(mgr.is_owner("/any/other/path"))


if __name__ == "__main__":
    unittest.main()
