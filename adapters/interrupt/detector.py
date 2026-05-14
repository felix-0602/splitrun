"""InterruptDetector — 检测是否有活跃 lane 正在执行中."""

from __future__ import annotations

from adapters.interrupt.schemas import InterruptContext


def is_lane_executing(lane_status: str | None) -> bool:
    """判断 lane 是否处于执行中（可被中断的状态）。"""
    if not lane_status:
        return False
    executing_statuses = {"active", "in_progress", "executing"}
    return lane_status.lower() in executing_statuses


def build_interrupt_context(
    current_state: str,
    current_milestone: str = "",
    current_lane: str | None = None,
    current_work_unit: str | None = None,
    lane_status: str | None = None,
    lane_wu_counts: dict[str, int] | None = None,
) -> InterruptContext:
    """从当前 DEEPSHIP 状态构建中断上下文快照。"""
    return InterruptContext(
        current_state=current_state,
        current_milestone=current_milestone,
        current_lane=current_lane,
        current_work_unit=current_work_unit,
        lane_status=lane_status,
        lane_wu_counts=lane_wu_counts or {},
    )


def should_enter_interrupt_routing(
    current_state: str,
    lane_status: str | None,
    message_complexity: str,
) -> bool:
    """判断是否应该进入中断路由流程。

    条件：
    - 消息复杂度 >= Small（非 chat/trivial）
    - 有活跃 lane 正在执行
    - 当前不在 IDLE/COMPLETE 终态
    """
    if message_complexity in ("chat", "trivial"):
        return False
    if not is_lane_executing(lane_status):
        return False
    if current_state in ("COMPLETE", "READ_CONTEXT"):
        return False
    return True
