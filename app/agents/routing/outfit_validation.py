"""Outfit 检查后的修正或结束路由。"""

from typing import Literal

from app.agents.state.shopping import ShoppingAgentState

OutfitValidationRoute = Literal[
    "correct_outfit",
    "end",
]


def route_after_outfit_validation(
    state: ShoppingAgentState,
) -> OutfitValidationRoute:
    """只允许首轮错误报告进入一次受限修正。"""

    recommendation = state.get(
        "outfit_recommendation",
    )
    report = state.get("outfit_feasibility_report")
    if recommendation is None or report is None or report.is_executable:
        return "end"
    if state.get("outfit_correction_attempts", 0) >= 1:
        return "end"
    return "correct_outfit"
