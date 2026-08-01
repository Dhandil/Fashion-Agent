"""确定性需求追问节点测试。"""

from langchain_core.messages import HumanMessage

from app.agents.nodes.clarify_requirements import (
    clarify_requirements,
)
from app.agents.schemas.requirements import (
    OutfitRequirementAnalysis,
    RequestIntent,
    RequirementField,
)


def test_clarification_only_asks_declared_missing_fields() -> None:
    """验证追问只包含结构化分析声明的最少字段。"""

    result = clarify_requirements(
        {
            "messages": [
                HumanMessage(content="帮我搭配"),
            ],
            "requirement_analysis": (
                OutfitRequirementAnalysis(
                    intent=RequestIntent.OUTFIT,
                    is_sufficient=False,
                    missing_fields=(
                        RequirementField.SCENARIO,
                        RequirementField.LOCATION,
                    ),
                )
            ),
        },
    )

    message = result["messages"][0].content
    assert "使用场景" in message
    assert "地点" in message
    assert "预算范围" not in message
