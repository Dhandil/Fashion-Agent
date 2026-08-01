"""结构化需求分析后的确定性路由。"""

from typing import Literal

from app.agents.schemas.requirements import (
    RequestIntent,
    ShoppingIntent,
)
from app.agents.state.shopping import ShoppingAgentState

RequirementRoute = Literal[
    "clarify",
    "general",
    "personalized",
]


def route_after_requirement_analysis(
    state: ShoppingAgentState,
) -> RequirementRoute:
    """根据充分度和主要意图选择最小必要的数据链路。"""

    analysis = state.get("requirement_analysis")
    if analysis is None:
        # 兼容分析节点降级前的旧状态，保留原个性化链路。
        return "personalized"
    if not analysis.is_sufficient:
        return "clarify"
    if analysis.needs_wardrobe or analysis.shopping_intent is ShoppingIntent.EXPLICIT:
        return "personalized"
    if analysis.intent in {
        RequestIntent.KNOWLEDGE,
        RequestIntent.OTHER,
    }:
        return "general"
    return "personalized"
