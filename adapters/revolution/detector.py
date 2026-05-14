"""RevolutionDetector — 识别"合理请求被 DEEPSHIP 框架约束拦住"的场景."""

from __future__ import annotations


def is_deepship_constraint(reason: str) -> bool:
    """判断拒绝原因是否来自 DEEPSHIP 框架约束（而非普通技术错误）。"""
    deepship_markers = [
        "DEEPSHIP BLOCK",
        "policy.code_write=false",
        "policy.doc_write=false",
        "policy.state_write=false",
        "policy.exec=false",
        "does not allow",
        "illegal transition",
        "outside current work unit files_allowed",
        "outside project root",
        "cannot directly edit DEEPSHIP metadata",
        "no current_work_unit",
    ]
    return any(marker.lower() in reason.lower() for marker in deepship_markers)


def is_reasonable_request(user_input: str) -> bool:
    """判断用户请求是否合理（非 trivial/恶意/明显错误）。"""
    if not user_input or not user_input.strip():
        return False
    if len(user_input.strip()) < 3:
        return False
    return True


def should_trigger_revolution(
    user_request: str,
    block_reason: str,
    is_normal_bug: bool = False,
    can_work_around: bool = False,
) -> tuple[bool, str]:
    """判断是否应触发革命提案。

    返回 (should_revolution, reason)。

    只在以下条件全部满足时触发：
    1. 用户请求合理
    2. 阻塞来自 DEEPSHIP 框架约束
    3. 不是普通 bug
    4. 无法通过正常路径绕过
    """
    if not is_reasonable_request(user_request):
        return False, "request is empty or trivial"

    if is_normal_bug:
        return False, "blocker is a normal bug — use REPAIR, not revolution"

    if can_work_around:
        return False, "task can be completed through a policy-allowed alternative path"

    if not is_deepship_constraint(block_reason):
        return False, "blocker is not a DEEPSHIP constraint — use normal debugging"

    return True, "reasonable request blocked by DEEPSHIP constraint — revolution may be appropriate"
