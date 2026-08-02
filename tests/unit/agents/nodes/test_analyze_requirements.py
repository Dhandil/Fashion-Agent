"""结构化需求分析节点测试。"""

import json
from unittest.mock import Mock

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage

from app.agents.nodes.analyze_requirements import (
    create_requirement_analysis_node,
)
from app.agents.schemas.requirements import (
    OutfitRequirementAnalysis,
    RequestIntent,
    ShoppingIntent,
)
from app.agents.state.shopping import ShoppingAgentState
from app.memory.short_term.conversation_summary import (
    ConversationSummary,
)


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


def test_analysis_respects_explicit_product_search_negation() -> None:
    """验证“不用查商品”同时收紧购物权限和错误购物意图。"""

    _, _, node = _create_node(
        OutfitRequirementAnalysis(
            intent=RequestIntent.SHOPPING,
            shopping_intent=ShoppingIntent.EXPLICIT,
        ),
    )

    result = node(
        {
            "messages": [
                HumanMessage(
                    content=("今天上海35度，给我通勤穿搭，不用查商品。"),
                ),
            ],
        },
    )
    analysis = result["requirement_analysis"]

    assert analysis.intent is RequestIntent.OUTFIT
    assert analysis.shopping_intent is ShoppingIntent.NONE


def test_analysis_does_not_infer_wardrobe_from_wearing_words() -> None:
    """验证“想穿黑色”不等于授权读取个人衣橱。"""

    _, _, node = _create_node(
        OutfitRequirementAnalysis(
            intent=RequestIntent.OUTFIT,
            scenario="通勤",
            needs_wardrobe=True,
            wardrobe_preferred=True,
        ),
    )

    result = node(
        {
            "messages": [
                HumanMessage(
                    content="这次通勤想穿黑色和简约风。",
                ),
            ],
        },
    )
    analysis = result["requirement_analysis"]

    assert analysis.needs_wardrobe is False
    assert analysis.wardrobe_preferred is False


def test_complete_weather_query_does_not_ask_for_weather() -> None:
    """验证地点和日期齐全后应查询工具，而不是追问天气事实。"""

    _, _, node = _create_node(
        OutfitRequirementAnalysis(
            intent=RequestIntent.OUTFIT,
            scenario="通勤",
            location="上海",
            target_date="明天",
            needs_weather=True,
            is_sufficient=False,
            missing_fields=("weather",),
        ),
    )

    result = node(
        {
            "messages": [
                HumanMessage(
                    content=("请按明天上海的天气搭配通勤服装。"),
                ),
            ],
        },
    )
    analysis = result["requirement_analysis"]

    assert analysis.is_sufficient is True
    assert analysis.missing_fields == ()
    assert analysis.needs_weather is True


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


def test_new_outfit_without_scenario_requires_clarification() -> None:
    """验证全新完整穿搭缺少场景时由确定性策略补充追问。"""

    _, _, node = _create_node(
        OutfitRequirementAnalysis(
            intent=RequestIntent.OUTFIT,
        ),
    )

    result = node(
        {
            "messages": [
                HumanMessage(content="帮我搭配一套衣服"),
            ],
        },
    )
    analysis = result["requirement_analysis"]

    assert analysis.is_sufficient is False
    assert analysis.missing_fields == ("scenario",)


def test_outfit_adjustment_can_reuse_previous_scenario() -> None:
    """验证局部调整不会被新穿搭的场景规则错误阻断。"""

    _, _, node = _create_node(
        OutfitRequirementAnalysis(
            intent=RequestIntent.OUTFIT_ADJUSTMENT,
            needs_wardrobe=True,
        ),
    )

    result = node(
        {
            "messages": [
                HumanMessage(content="把刚才那套改正式一点"),
            ],
        },
    )
    analysis = result["requirement_analysis"]

    assert analysis.is_sufficient is True
    assert analysis.missing_fields == ()


def test_weekend_signal_is_enough_for_basic_outfit() -> None:
    """验证周末等明确情境不会因模型字段归类差异被错误追问。"""

    _, _, node = _create_node(
        OutfitRequirementAnalysis(
            intent=RequestIntent.OUTFIT,
            target_date="周末",
            wardrobe_preferred=True,
            needs_wardrobe=True,
            is_sufficient=False,
            missing_fields=("scenario",),
        ),
    )

    result = node(
        {
            "messages": [
                HumanMessage(
                    content=("只用我的衣橱搭配周末穿搭，我不想买新衣服。"),
                ),
            ],
        },
    )
    analysis = result["requirement_analysis"]

    assert analysis.is_sufficient is True
    assert analysis.missing_fields == ()
    assert analysis.shopping_intent is ShoppingIntent.NONE


def test_current_avoidance_overrides_same_preference() -> None:
    """验证本轮明确避免项会移除模型输出中的同项喜欢偏好。"""

    _, _, node = _create_node(
        OutfitRequirementAnalysis(
            intent=RequestIntent.OUTFIT,
            scenario="面试",
            style_preferences=("街头风", "简约"),
            color_preferences=("黑色", "米白"),
            avoided_styles=("街头风",),
            avoided_colors=("黑色",),
            avoided_materials=("羊毛",),
        ),
    )

    result = node(
        {
            "messages": [
                HumanMessage(
                    content=("这次面试不要街头风和黑色，也不要羊毛。"),
                ),
            ],
        },
    )
    analysis = result["requirement_analysis"]

    assert analysis.style_preferences == ("简约",)
    assert analysis.color_preferences == ("米白",)
    assert analysis.avoided_styles == ("街头风",)
    assert analysis.avoided_colors == ("黑色",)
    assert analysis.avoided_materials == ("羊毛",)


def test_summary_is_non_authoritative_for_current_avoidances() -> None:
    """验证历史摘要不会被提升为本轮明确避雷或重复近期消息。"""

    _, structured_model, node = _create_node(
        OutfitRequirementAnalysis(
            intent=RequestIntent.OUTFIT,
            scenario="通勤",
            color_preferences=("白色",),
            avoided_colors=("黑色",),
        ),
    )
    state: ShoppingAgentState = {
        "messages": [
            HumanMessage(content="以前不要黑色"),
            AIMessage(content="好的"),
            HumanMessage(content="这次通勤穿白色"),
        ],
        "conversation_summary": ConversationSummary(
            content="用户：以前不要黑色\n助手：好的",
            covered_message_count=2,
        ),
    }

    result = node(state)

    analysis = result["requirement_analysis"]
    assert analysis.avoided_colors == ()
    assert analysis.color_preferences == ("白色",)

    sent_messages = structured_model.invoke.call_args.args[0]
    payload = json.loads(sent_messages[1].content)
    assert payload["conversation_summary"] == ("用户：以前不要黑色\n助手：好的")
    assert payload["recent_conversation"] == [
        {
            "role": "user",
            "content": "这次通勤穿白色",
        },
    ]
