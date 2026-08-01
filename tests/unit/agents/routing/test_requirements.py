"""需求分析后的确定性路由测试。"""

from langchain_core.messages import HumanMessage

from app.agents.routing.requirements import (
    route_after_requirement_analysis,
)
from app.agents.schemas.requirements import (
    OutfitRequirementAnalysis,
    RequestIntent,
    RequirementField,
    ShoppingIntent,
)


def test_incomplete_requirement_routes_to_clarification() -> None:
    """验证信息不足时不读取动态数据。"""

    route = route_after_requirement_analysis(
        {
            "messages": [HumanMessage(content="怎么穿")],
            "requirement_analysis": (
                OutfitRequirementAnalysis(
                    intent=RequestIntent.OUTFIT,
                    is_sufficient=False,
                    missing_fields=(RequirementField.SCENARIO,),
                )
            ),
        },
    )

    assert route == "clarify"


def test_knowledge_requirement_uses_general_route() -> None:
    """验证通用知识问题绕过用户个性化数据。"""

    route = route_after_requirement_analysis(
        {
            "messages": [HumanMessage(content="亚麻怎么洗")],
            "requirement_analysis": (
                OutfitRequirementAnalysis(
                    intent=RequestIntent.KNOWLEDGE,
                )
            ),
        },
    )

    assert route == "general"


def test_explicit_shopping_uses_personalized_route() -> None:
    """验证明确购物可以读取穿搭偏好后再查询商品。"""

    route = route_after_requirement_analysis(
        {
            "messages": [HumanMessage(content="买衬衫")],
            "requirement_analysis": (
                OutfitRequirementAnalysis(
                    intent=RequestIntent.OTHER,
                    shopping_intent=(ShoppingIntent.EXPLICIT),
                )
            ),
        },
    )

    assert route == "personalized"
