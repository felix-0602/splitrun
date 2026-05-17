"""
Lane status aggregation contract tests — index.json + report.json → lane status dicts.

核心契约: aggregate_lane_status() 的转换规则。
splitrun-status Step 2-4 和 splitrun-land Step 1-2 依赖此转换的正确性。
"""

import unittest
from adapters.gates import (
    aggregate_lane_status,
    determine_land_status,
    LAND_OK,
    LAND_WAITING,
    LAND_BLOCKED,
    LAND_BOUNDARY,
    LAND_NOTHING,
)


# ── helpers ────────────────────────────────────────────────────────

def _index_entry(status="active", worktree="/tmp/LANE-001", files_claimed=None, **extra):
    entry = {
        "status": status,
        "task": "fix auth bug",
        "worktree": worktree,
        "files_claimed": files_claimed or ["src/"],
        "spawned_at": "2026-05-17T10:00:00Z",
    }
    entry.update(extra)
    return entry


_DEFAULT_CHANGED = ["src/auth.py"]


def _report(status="done", changed_files=_DEFAULT_CHANGED, test_results="3/3 passed", result="done"):
    return {
        "lane_id": "LANE-001",
        "status": status,
        "changed_files": changed_files,
        "test_results": test_results,
        "result": result,
    }


def _make_reader(reports_by_worktree: dict):
    """工厂：按 worktree 路径返回对应的 report dict 或 None。"""
    def reader(wt):
        return reports_by_worktree.get(wt)
    return reader


# ── tests ──────────────────────────────────────────────────────────

class AggregateLaneStatusTest(unittest.TestCase):
    """aggregate_lane_status 转换规则。"""

    def test_empty_index_returns_empty_list(self):
        self.assertEqual(aggregate_lane_status({}), [])

    def test_no_report_keeps_index_status(self):
        """无 report 时，status 沿用 index 原值，证据全部缺省。"""
        index = {"LANE-001": _index_entry(status="active")}
        reader = _make_reader({})  # 所有 worktree 都无 report

        result = aggregate_lane_status(index, report_reader=reader)
        self.assertEqual(len(result), 1)
        lane = result[0]
        self.assertEqual(lane["lane_id"], "LANE-001")
        self.assertEqual(lane["status"], "active")
        self.assertFalse(lane["has_report"])
        self.assertFalse(lane["has_test_results"])
        self.assertIsNone(lane["boundary_pass"])

    def test_done_report_sets_status_done(self):
        """report status=done 覆盖 index status=active → effective status=done。"""
        index = {"LANE-001": _index_entry(status="active", worktree="/tmp/LANE-001")}
        report = _report(status="done")
        reader = _make_reader({"/tmp/LANE-001": report})

        result = aggregate_lane_status(index, report_reader=reader)
        self.assertEqual(result[0]["status"], "done")
        self.assertTrue(result[0]["has_report"])
        self.assertTrue(result[0]["has_test_results"])

    def test_blocked_report_sets_status_blocked(self):
        index = {"LANE-001": _index_entry(status="active", worktree="/tmp/LANE-001")}
        report = _report(status="blocked", test_results="")
        reader = _make_reader({"/tmp/LANE-001": report})

        result = aggregate_lane_status(index, report_reader=reader)
        self.assertEqual(result[0]["status"], "blocked")
        self.assertTrue(result[0]["has_report"])
        self.assertFalse(result[0]["has_test_results"])  # 空字符串

    def test_empty_test_results_is_falsy(self):
        """test_results 为空字符串 → has_test_results=False。"""
        index = {"LANE-001": _index_entry(worktree="/tmp/LANE-001")}
        report = _report(test_results="")
        reader = _make_reader({"/tmp/LANE-001": report})

        result = aggregate_lane_status(index, report_reader=reader)
        self.assertFalse(result[0]["has_test_results"])

    def test_zero_test_results_is_truthy(self):
        """test_results='0/3 passed' 非空字符串 → has_test_results=True。"""
        index = {"LANE-001": _index_entry(worktree="/tmp/LANE-001")}
        report = _report(test_results="0/3 passed")
        reader = _make_reader({"/tmp/LANE-001": report})

        result = aggregate_lane_status(index, report_reader=reader)
        self.assertTrue(result[0]["has_test_results"])

    def test_boundary_in_bounds(self):
        """changed_files 全部在 files_claimed 内 → boundary_pass=True。"""
        index = {"LANE-001": _index_entry(
            worktree="/tmp/LANE-001",
            files_claimed=["src/"],
        )}
        report = _report(changed_files=["src/auth.py", "src/login.py"])
        reader = _make_reader({"/tmp/LANE-001": report})

        result = aggregate_lane_status(index, report_reader=reader)
        self.assertTrue(result[0]["boundary_pass"])

    def test_boundary_out_of_bounds(self):
        """changed_files 有越界 → boundary_pass=False。"""
        index = {"LANE-001": _index_entry(
            worktree="/tmp/LANE-001",
            files_claimed=["src/"],
        )}
        report = _report(changed_files=["src/auth.py", "utils/helper.py"])
        reader = _make_reader({"/tmp/LANE-001": report})

        result = aggregate_lane_status(index, report_reader=reader)
        self.assertFalse(result[0]["boundary_pass"])

    def test_boundary_no_changed_files(self):
        """report 没有 changed_files → boundary_pass=None（未检查）。"""
        index = {"LANE-001": _index_entry(worktree="/tmp/LANE-001")}
        report = _report(changed_files=[])
        reader = _make_reader({"/tmp/LANE-001": report})

        result = aggregate_lane_status(index, report_reader=reader)
        self.assertIsNone(result[0]["boundary_pass"])

    def test_report_invalid_json_treated_as_no_report(self):
        """report.json 损坏 → 等同无 report。"""
        index = {"LANE-001": _index_entry(worktree="/tmp/LANE-001")}

        def bad_reader(wt):
            raise Exception("corrupted")
        # _default_report_reader catches JSONDecodeError/OSError,
        # but injected reader can throw anything → should be caught upstream.
        # aggregate_lane_status 不替 caller 吞异常；caller 应自己处理。
        # 这里验证 aggregate 调用 reader 的路径。
        with self.assertRaises(Exception):
            aggregate_lane_status(index, report_reader=bad_reader)

    def test_empty_worktree_no_report(self):
        """worktree 路径为空 → 不尝试读 report。"""
        index = {"LANE-001": _index_entry(worktree="")}
        calls = []

        def tracking_reader(wt):
            calls.append(wt)
            return None

        result = aggregate_lane_status(index, report_reader=tracking_reader)
        # reader 不应被调用（worktree 为空）
        self.assertEqual(calls, [])
        self.assertFalse(result[0]["has_report"])

    def test_multiple_lanes_mixed(self):
        """混合场景：done + active + blocked。"""
        index = {
            "LANE-001": _index_entry(status="active", worktree="/tmp/LANE-001", files_claimed=["src/"]),
            "LANE-002": _index_entry(status="active", worktree="/tmp/LANE-002", files_claimed=["docs/"]),
            "LANE-003": _index_entry(status="active", worktree="/tmp/LANE-003", files_claimed=["tests/"]),
        }
        reader = _make_reader({
            "/tmp/LANE-001": _report(status="done", changed_files=["src/auth.py"]),
            "/tmp/LANE-002": _report(status="blocked", changed_files=[], test_results=""),
            # LANE-003 无 report
        })

        result = aggregate_lane_status(index, report_reader=reader)
        self.assertEqual(len(result), 3)

        lane1 = [l for l in result if l["lane_id"] == "LANE-001"][0]
        self.assertEqual(lane1["status"], "done")
        self.assertTrue(lane1["boundary_pass"])

        lane2 = [l for l in result if l["lane_id"] == "LANE-002"][0]
        self.assertEqual(lane2["status"], "blocked")
        self.assertIsNone(lane2["boundary_pass"])

        lane3 = [l for l in result if l["lane_id"] == "LANE-003"][0]
        self.assertEqual(lane3["status"], "active")
        self.assertFalse(lane3["has_report"])


class AggregateToLandDeterminationTest(unittest.TestCase):
    """aggregate_lane_status → determine_land_status 端到端。"""

    def test_e2e_can_land(self):
        """全部 done + 都有测试结果 + 无越界 → CAN LAND。"""
        index = {
            "LANE-001": _index_entry(worktree="/tmp/LANE-001", files_claimed=["src/"]),
            "LANE-002": _index_entry(worktree="/tmp/LANE-002", files_claimed=["docs/"]),
        }
        reader = _make_reader({
            "/tmp/LANE-001": _report(status="done", changed_files=["src/auth.py"]),
            "/tmp/LANE-002": _report(status="done", changed_files=["docs/readme.md"]),
        })

        lanes = aggregate_lane_status(index, report_reader=reader)
        self.assertEqual(determine_land_status(lanes), LAND_OK)

    def test_e2e_boundary_violation(self):
        """有越界 → CANNOT LAND — boundary。"""
        index = {
            "LANE-001": _index_entry(worktree="/tmp/LANE-001", files_claimed=["src/"]),
        }
        reader = _make_reader({
            "/tmp/LANE-001": _report(
                status="done",
                changed_files=["src/auth.py", "utils/helper.py"],
            ),
        })

        lanes = aggregate_lane_status(index, report_reader=reader)
        self.assertEqual(determine_land_status(lanes), LAND_BOUNDARY)

    def test_e2e_blocked(self):
        """有 blocked lane → CANNOT LAND — blocked。"""
        index = {
            "LANE-001": _index_entry(worktree="/tmp/LANE-001", files_claimed=["src/"]),
            "LANE-002": _index_entry(worktree="/tmp/LANE-002", files_claimed=["docs/"]),
        }
        reader = _make_reader({
            "/tmp/LANE-001": _report(status="done", changed_files=["src/auth.py"]),
            "/tmp/LANE-002": _report(status="blocked", changed_files=[], test_results=""),
        })

        lanes = aggregate_lane_status(index, report_reader=reader)
        self.assertEqual(determine_land_status(lanes), LAND_BLOCKED)

    def test_e2e_still_executing(self):
        """有 lane 无 report → CANNOT LAND — waiting。"""
        index = {
            "LANE-001": _index_entry(worktree="/tmp/LANE-001", files_claimed=["src/"]),
            "LANE-002": _index_entry(worktree="/tmp/LANE-002", files_claimed=["docs/"]),
        }
        reader = _make_reader({
            "/tmp/LANE-001": _report(status="done", changed_files=["src/auth.py"]),
            # LANE-002 无 report
        })

        lanes = aggregate_lane_status(index, report_reader=reader)
        self.assertEqual(determine_land_status(lanes), LAND_WAITING)

    def test_e2e_no_lanes(self):
        self.assertEqual(determine_land_status([]), LAND_NOTHING)


if __name__ == "__main__":
    unittest.main()
