"""RevolutionProposalBuilder — 构建革命提案（无副作用，批准前不修改任何文件）."""

from __future__ import annotations

from adapters.revolution.schemas import (
    BlockingConstraint,
    ProposedChange,
    RevolutionProposal,
    RollbackPlan,
)


def build_proposal(
    original_request: str,
    why_reasonable: str,
    constraint_source: str,
    constraint_rule: str,
    what_constraint_protects: str,
    current_behavior: str,
    proposed_description: str,
    target_files: list[str],
    change_type: str,
    impact: str,
    risks: str,
    approval_needed: str,
    rollback_steps: list[str],
    rollback_verification: str,
) -> RevolutionProposal:
    """构建一个完整的 RevolutionProposal。

    此函数无副作用 — 仅返回 dataclass，不写任何文件。
    调用者负责将提案呈现给用户审批。
    """
    constraint = BlockingConstraint(
        constraint_source=constraint_source,
        constraint_rule=constraint_rule,
        what_it_protects=what_constraint_protects,
        current_behavior=current_behavior,
    )

    change = ProposedChange(
        description=proposed_description,
        target_files=tuple(target_files),
        change_type=change_type,
        impact=impact,
    )

    rollback = RollbackPlan(
        steps=tuple(rollback_steps),
        verification=rollback_verification,
    )

    return RevolutionProposal(
        original_request=original_request,
        reason_it_is_reasonable=why_reasonable,
        blocking_constraint=constraint,
        proposed_change=change,
        risks=risks,
        approval_needed=approval_needed,
        rollback_plan=rollback,
        status="awaiting_approval",
    )


def format_proposal_for_user(proposal: RevolutionProposal) -> str:
    """将 RevolutionProposal 格式化为面向用户的共识弹窗文案。"""
    bc = proposal.blocking_constraint
    pc = proposal.proposed_change
    rp = proposal.rollback_plan

    lines = [
        "我判断你的请求是合理的，但当前 DEEPSHIP 的一个框架约束阻止了我继续执行。",
        "",
        f"**请求：** {proposal.original_request}",
        "",
        f"**为什么合理：** {proposal.reason_it_is_reasonable}",
        "",
        f"**被拦住的位置：** {bc.constraint_source}",
        f"> {bc.constraint_rule}",
        "",
        f"**这个约束原本的作用：** {bc.what_it_protects}",
        "",
        "**如果要继续，我建议对 DEEPSHIP 做一次受控自进化：**",
        f"- 改动描述：{pc.description}",
        f"- 涉及文件：{', '.join(pc.target_files)}",
        f"- 改动类型：{pc.change_type}",
        f"- 预期影响：{pc.impact}",
        "",
        f"**可能风险：** {proposal.risks}",
        "",
        f"**需要你批准：** {proposal.approval_needed}",
        "",
        "**批准后我会：**",
        "1. 创建 self-evolution lane",
        "2. 修改最小必要源码",
        "3. 增加测试",
        "4. 记录审计日志",
        "5. 回到原任务继续执行",
        "",
        f"**回滚方式：** {'; '.join(rp.steps)}",
        f"**回滚验证：** {rp.verification}",
        "",
        '请明确回复"批准革命"后我才会修改 DEEPSHIP 框架约束源码。',
    ]
    return "\n".join(lines)
