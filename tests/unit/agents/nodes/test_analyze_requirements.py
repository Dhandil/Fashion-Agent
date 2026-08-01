"""结构化需求分析节点测试。"""

from unittest.mock import Mock

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage

from app.agents.nodes.analyze_requirements import (
    create_requirement_analysis_node,
)
from app.agents.schemas.requirements import (
    OutfitRequirementAnalysis,
    RequestIntent,
    ShoppingIntent,
)
from app.agents.state.shopping import ShoppingAgentState


def _create_node(
    structured_result: object,
) -> tuple[Mock, Mock, object]:
    """创建需求节点测试使用的模型替身。"""

    model = Mock(spec=BaseChatModel)
    structured_model = Mock()
    model.with_structured_output.return_value = structured_model
    structured_model.invoke.return_value = structured_result
    return (
        model,
        structured_model,
        create_requirement_analysis_node(model),
    )


def test_analysis_does_not_expand_shopping_permission() -> None:
    """验证模型不能把普通穿搭请求扩大为商品查询。"""

    _, _, node = _create_node(
        OutfitRequirementAnalysis(
            intent=RequestIntent.OUTFIT,
            shopping_intent=ShoppingIntent.EXPLICIT,
        ),
    )
    state: ShoppingAgentState = {
        "messages": [
            HumanMessage(
                content="帮我搭配一套夏季通勤服装",
            ),
        ],
    }

    result = node(state)

    assert result["requirement_analysis"].shopping_intent is ShoppingIntent.NONE


def test_analysis_recognises_explicit_product_search() -> None:
    """验证用户原文明示找商品时开放商品查询权限。"""

    _, _, node = _create_node(
        OutfitRequirementAnalysis(
            intent=RequestIntent.OTHER,
        ),
    )
    state: ShoppingAgentState = {
        "messages": [
            HumanMessage(
                content="帮我找一件价格不超过 300 元的衬衫",
            ),
        ],
    }

    result = node(state)

    assert result["requirement_analysis"].shopping_intent is ShoppingIntent.EXPLICIT


def test_analysis_falls_back_without_blocking_request() -> None:
    """验证结构化供应商失败时使用保守规则继续请求。"""

    model = Mock(spec=BaseChatModel)
    structured_model = Mock()
    model.with_structured_output.return_value = structured_model
    structured_model.invoke.side_effect = RuntimeError(
        "provider unavailable",
    )
    node = create_requirement_analysis_node(model)

    result = node(
        {
            "messages": [
                HumanMessage(
                    content="我想购买一件亚麻衬衫",
                ),
            ],
        },
    )
    analysis = result["requirement_analysis"]

    assert analysis.is_sufficient is True
    assert analysis.intent is RequestIntent.SHOPPING
    assert analysis.shopping_intent is ShoppingIntent.EXPLICIT
