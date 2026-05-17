"""
Land determination gate contract tests — deepship-status Step 4 + deepship-land 前置。

核心契约: CAN LAND / CANNOT LAND 判定规则的 5 种状态。
"""

import unittest
from adapters.gates import (
    determine_land_status,
    LAND_OK,
    LAND_WAITING,
    LAND_BLOCKED,
    LAND_BOUNDARY,
    LAND_NOTHING,
)


def _lane(status, has_report=True, has_test_results=True, boundary_pass=True):
    return {
        "lane_id": "LANE-001",
        "status": status,
        "has_report": has_report,
        "has_test_results": has_test_results,
        "boundary_pass": boundary_pass,
    }


class LandDeterminationTest(unittest.TestCase):
    """CAN LAND 判定门禁。"""

    def test_no_lanes_nothing_to_land(self):
        self.assertEqual(determine_land_status([]), LAND_NOTHING)

    def test_all_done_clean_can_land(self):
        lanes = [
            _lane("done"),
            _lane("done"),
        ]
        self.assertEqual(determine_land_status(lanes), LAND_OK)

    def test_single_lane_done_can_land(self):
        self.assertEqual(determine_land_status([_lane("done")]), LAND_OK)

    def test_active_without_report_is_waiting(self):
        lanes = [
            _lane("done"),
            _lane("active", has_report=False),
        ]
        self.assertEqual(determine_land_status(lanes), LAND_WAITING)

    def test_blocked_lane_blocks_land(self):
        lanes = [
            _lane("done"),
            _lane("blocked", has_report=True, has_test_results=False),
        ]
        self.assertEqual(determine_land_status(lanes), LAND_BLOCKED)

    def test_boundary_failure_blocks_land(self):
        lanes = [
            _lane("done"),
            _lane("done", boundary_pass=False),
        ]
        self.assertEqual(determine_land_status(lanes), LAND_BOUNDARY)

    def test_missing_test_results_is_waiting(self):
        lanes = [
            _lane("done", has_test_results=False),
        ]
        self.assertEqual(determine_land_status(lanes), LAND_WAITING)

    def test_mixed_scenario_priority(self):
        """blocked 优先于 waiting 优先于 boundary —— 先报告最严重的问题。"""
        lanes = [
            _lane("done"),
            _lane("done", boundary_pass=False),
            _lane("active", has_report=False),
            _lane("blocked"),
        ]
        # blocked 优先级最高
        self.assertEqual(determine_land_status(lanes), LAND_BLOCKED)

    def test_done_lane_without_report_not_can_land(self):
        """done 但没有 report 是证据不完整，不能 land。"""
        lanes = [
            _lane("done", has_report=False),
        ]
        self.assertEqual(determine_land_status(lanes), LAND_WAITING)

    def test_done_lane_boundary_unknown_not_can_land(self):
        """boundary_pass=None（未检查）不能等同于通过，不能 land。"""
        lanes = [
            _lane("done", boundary_pass=None),
        ]
        self.assertEqual(determine_land_status(lanes), LAND_WAITING)

    def test_done_lane_missing_report_and_boundary_unknown(self):
        """多个证据缺口同时存在。"""
        lanes = [
            _lane("done", has_report=False, boundary_pass=None, has_test_results=False),
        ]
        self.assertEqual(determine_land_status(lanes), LAND_WAITING)

    def test_all_three_evidences_explicit_true_can_land(self):
        """report + test_results + boundary_pass 三者显式 True 才能 land。"""
        lanes = [
            _lane("done", has_report=True, has_test_results=True, boundary_pass=True),
        ]
        self.assertEqual(determine_land_status(lanes), LAND_OK)


if __name__ == "__main__":
    unittest.main()
