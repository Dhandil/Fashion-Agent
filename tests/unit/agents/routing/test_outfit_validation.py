"""Outfit 检查后的单次修正路由测试。"""

from langchain_core.messages import HumanMessage

from app.agents.routing.outfit_validation import (
    route_after_outfit_validation,
)
from app.domain.entities.outfit import (
    OutfitItem,
    OutfitRecommendation,
)
from app.domain.entities.outfit_validation import (
    OutfitFeasibilityIssue,
    OutfitFeasibilityReport,
    OutfitIssueCode,
    OutfitIssueSeverity,
)


def _invalid_state(attempts: int) -> dict:
    """创建具有一个阻断错误的验证状态。"""

    return {
        "messages": [HumanMessage(content="帮我搭配")],
        "outfit_recommendation": OutfitRecommendation(
            name="不完整方案",
            scenario="通勤",
            items=(
                OutfitItem(
                    role="上装",
                    name="白色衬衫",
                    source="recommendation",
                ),
            ),
            recommendation_reason="缺少核心单品。",
        ),
        "outfit_feasibility_report": (
            OutfitFeasibilityReport(
                is_executable=False,
                issues=(
                    OutfitFeasibilityIssue(
                        code=(OutfitIssueCode.MISSING_CORE_ROLE),
                        severity=OutfitIssueSeverity.ERROR,
                        message="缺少下装和鞋履。",
                    ),
                ),
            )
        ),
        "outfit_correction_attempts": attempts,
    }


def test_first_failure_routes_to_correction() -> None:
    """验证首次错误报告获得唯一一次修正机会。"""

    assert (
        route_after_outfit_validation(
            _invalid_state(attempts=0),
        )
        == "correct_outfit"
    )


def test_second_failure_routes_to_end() -> None:
    """验证修正后仍失败时立即结束，不形成循环。"""

    assert (
        route_after_outfit_validation(
            _invalid_state(attempts=1),
        )
        == "end"
    )


def test_executable_outfit_routes_to_end() -> None:
    """验证通过检查的方案不会进入修正节点。"""

    state = _invalid_state(attempts=0)
    state["outfit_feasibility_report"] = OutfitFeasibilityReport(
        is_executable=True,
    )

    assert route_after_outfit_validation(state) == "end"
