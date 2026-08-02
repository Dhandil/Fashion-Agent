"""结构化 Outfit 生成节点测试。"""

import json
from unittest.mock import Mock

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    HumanMessage,
    ToolMessage,
)

from app.agents.nodes.generate_outfit import (
    OUTFIT_GENERATION_SYSTEM_PROMPT,
    create_outfit_generation_node,
)
from app.agents.schemas.outfit import (
    OutfitGenerationResult,
)
from app.agents.schemas.requirements import (
    OutfitRequirementAnalysis,
    RequestIntent,
)
from app.agents.schemas.style_profile import (
    StyleProfileSnapshot,
)
from app.agents.state.shopping import ShoppingAgentState
from app.domain.entities.outfit import (
    OutfitItem,
    OutfitRecommendation,
)
from app.domain.entities.weather import WeatherContext


def create_current_turn_messages() -> list[AnyMessage]:
    """创建包含一次衣橱查询的当前轮消息。"""

    return [
        HumanMessage(
            content="请用我的衣橱搭配夏季通勤服装",
        ),
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "search_wardrobe",
                    "args": {
                        "category": "衬衫",
                    },
                    "id": "wardrobe-call-1",
                    "type": "tool_call",
                },
            ],
        ),
        ToolMessage(
            name="search_wardrobe",
            tool_call_id="wardrobe-call-1",
            content=json.dumps(
                [
                    {
                        "wardrobe_item_id": "shirt-001",
                        "name": "浅蓝色亚麻衬衫",
                        "category": "衬衫",
                        "status": "available",
                    },
                ],
                ensure_ascii=False,
            ),
        ),
        AIMessage(
            content="建议使用浅蓝色亚麻衬衫完成通勤搭配。",
        ),
    ]


def create_recommendation(
    wardrobe_item_id: str = "shirt-001",
) -> OutfitRecommendation:
    """创建引用指定衣橱单品的结构化推荐。"""

    return OutfitRecommendation(
        name="清爽夏季通勤",
        scenario="通勤",
        season="夏季",
        items=[
            OutfitItem(
                role="上装",
                name="浅蓝色亚麻衬衫",
                source="wardrobe",
                source_reference_id=wardrobe_item_id,
                reason="透气且适合通勤",
            ),
        ],
        recommendation_reason="使用已有亚麻衬衫保持清爽。",
    )


def test_generate_outfit_accepts_traceable_wardrobe_id() -> None:
    """验证节点接受来自当前轮衣橱工具的 ID。"""

    model = Mock(spec=BaseChatModel)
    structured_model = Mock()
    model.with_structured_output.return_value = structured_model

    recommendation = create_recommendation()
    structured_model.invoke.return_value = OutfitGenerationResult(
        outfit=recommendation,
    )

    generate_outfit = create_outfit_generation_node(
        model,
    )
    state: ShoppingAgentState = {
        "messages": create_current_turn_messages(),
        "knowledge_context": "亚麻适合炎热天气。",
        "outfit_feedback_context": ("用户喜欢简约清爽的历史穿搭。"),
        "style_profile_context": ("用户明确维护的喜欢风格：休闲。"),
        "recent_outfits_context": ("近期已经使用 shirt-002 完成通勤搭配。"),
        "previous_outfit_recommendation": (create_recommendation()),
        "weather_context": WeatherContext(
            location="上海",
            target_date="2026-08-01",
            condition="阵雨",
            temperature_max_c=33,
            precipitation_probability=70,
            source="user_provided",
        ),
    }

    result = generate_outfit(state)

    assert result == {
        "outfit_recommendation": recommendation,
    }
    model.with_structured_output.assert_called_once_with(
        OutfitGenerationResult,
        method="json_mode",
    )

    # 结构化模型应同时看到工具证据和服装知识
    structured_messages = structured_model.invoke.call_args.args[0]
    assert OUTFIT_GENERATION_SYSTEM_PROMPT in (structured_messages[0].content)
    assert "shirt-001" in (structured_messages[1].content)
    assert "亚麻适合炎热天气" in (structured_messages[1].content)
    assert "用户喜欢简约清爽" in (structured_messages[1].content)
    assert "用户明确维护的喜欢风格" in (structured_messages[1].content)
    assert "近期已经使用 shirt-002" in (structured_messages[1].content)
    assert '"previous_outfit"' in (structured_messages[1].content)
    assert "清爽夏季通勤" in (structured_messages[1].content)
    assert '"provided_weather"' in (structured_messages[1].content)
    assert '"precipitation_probability": 70' in (structured_messages[1].content)
    assert '"weather_outfit_guidance"' in (structured_messages[1].content)
    assert "高温或体感炎热" in (structured_messages[1].content)
    assert "output_schema" in (structured_messages[1].content)


def test_generate_outfit_defers_wardrobe_id_validation() -> None:
    """验证生成节点把来源 ID 校验交给后续可执行性节点。"""

    model = Mock(spec=BaseChatModel)
    structured_model = Mock()
    model.with_structured_output.return_value = structured_model
    structured_model.invoke.return_value = OutfitGenerationResult(
        outfit=create_recommendation(
            wardrobe_item_id="invented-shirt",
        ),
    )

    generate_outfit = create_outfit_generation_node(
        model,
    )
    state: ShoppingAgentState = {
        "messages": create_current_turn_messages(),
    }

    result = generate_outfit(state)

    assert result["outfit_recommendation"] is not None
    assert result["outfit_recommendation"].items[0].source_reference_id == "invented-shirt"


def test_generate_outfit_includes_weather_tool_result() -> None:
    """验证真实天气工具结果进入结构化生成上下文。"""

    model = Mock(spec=BaseChatModel)
    structured_model = Mock()
    model.with_structured_output.return_value = structured_model
    structured_model.invoke.return_value = OutfitGenerationResult(
        outfit=create_recommendation(),
    )
    messages = create_current_turn_messages()
    messages.insert(
        -1,
        ToolMessage(
            name="get_weather",
            tool_call_id="weather-call-1",
            content=json.dumps(
                [
                    {
                        "location": "上海",
                        "target_date": "2026-08-01",
                        "condition": "阵雨",
                        "temperature_max_c": 33,
                        "source": "api",
                    },
                ],
                ensure_ascii=False,
            ),
        ),
    )
    generate_outfit = create_outfit_generation_node(
        model,
    )

    result = generate_outfit(
        {
            "messages": messages,
        },
    )

    assert result["outfit_recommendation"] is not None
    generation_message = structured_model.invoke.call_args.args[0][1]
    assert '"weather_tool_results"' in (generation_message.content)
    assert '"condition": "阵雨"' in (generation_message.content)
    assert "高温或体感炎热" in (generation_message.content)


def test_generate_outfit_defers_product_id_validation() -> None:
    """验证商品 ID 同样由独立可执行性节点统一校验。"""

    model = Mock(spec=BaseChatModel)
    structured_model = Mock()
    model.with_structured_output.return_value = structured_model

    recommendation = OutfitRecommendation(
        name="夏季通勤搭配",
        scenario="通勤",
        items=[
            OutfitItem(
                role="上装",
                name="亚麻衬衫",
                source="product",
                source_reference_id="invented-product",
                reason="透气并适合通勤",
            ),
        ],
        recommendation_reason="选择透气的亚麻衬衫。",
    )
    structured_model.invoke.return_value = OutfitGenerationResult(
        outfit=recommendation,
    )

    messages = create_current_turn_messages()
    messages.insert(
        -1,
        ToolMessage(
            name="search_products",
            tool_call_id="product-call-1",
            content=json.dumps(
                [
                    {
                        "product_id": "product-001",
                        "name": "亚麻衬衫",
                    },
                ],
                ensure_ascii=False,
            ),
        ),
    )

    generate_outfit = create_outfit_generation_node(
        model,
    )
    state: ShoppingAgentState = {
        "messages": messages,
    }

    result = generate_outfit(state)

    assert result["outfit_recommendation"] is recommendation


def test_generate_outfit_allows_model_to_skip_outfit() -> None:
    """验证查看衣橱等请求可以不生成完整 Outfit。"""

    model = Mock(spec=BaseChatModel)
    structured_model = Mock()
    model.with_structured_output.return_value = structured_model
    structured_model.invoke.return_value = OutfitGenerationResult(
        outfit=None,
    )

    generate_outfit = create_outfit_generation_node(
        model,
    )
    state: ShoppingAgentState = {
        "messages": create_current_turn_messages(),
    }

    assert generate_outfit(state) == {
        "outfit_recommendation": None,
    }


def test_generate_outfit_returns_gap_without_calling_model() -> None:
    """验证衣橱核心角色不足时直接返回缺口且不浪费模型调用。"""

    model = Mock(spec=BaseChatModel)
    structured_model = Mock()
    model.with_structured_output.return_value = structured_model
    generate_outfit = create_outfit_generation_node(model)
    state: ShoppingAgentState = {
        "messages": [
            HumanMessage(content="用我的衣橱搭配通勤服装"),
            ToolMessage(
                name="search_wardrobe",
                tool_call_id="wardrobe-gap-call",
                content=json.dumps(
                    [
                        {
                            "wardrobe_item_id": "upper-only",
                            "name": "白色衬衫",
                            "category": "上装",
                            "status": "available",
                        },
                    ],
                    ensure_ascii=False,
                ),
            ),
        ],
        "requirement_analysis": (
            OutfitRequirementAnalysis(
                intent=RequestIntent.OUTFIT,
                scenario="通勤",
                needs_wardrobe=True,
            )
        ),
    }

    result = generate_outfit(state)

    assert result["outfit_recommendation"] is None
    gap_report = result["outfit_gap_report"]
    assert [role.value for role in gap_report.missing_roles] == ["下装", "鞋履"]
    assert gap_report.shopping_search_allowed is False
    assert "不会自动查询商品" in (result["messages"][0].content)
    structured_model.invoke.assert_not_called()


def test_generate_outfit_discards_invalid_structured_result() -> None:
    """验证结构不完整时保留文本回复并丢弃 Outfit。"""

    model = Mock(spec=BaseChatModel)
    structured_model = Mock()
    model.with_structured_output.return_value = structured_model
    structured_model.invoke.return_value = {
        "outfit": {
            "name": "不完整搭配",
        },
    }

    generate_outfit = create_outfit_generation_node(
        model,
    )
    state: ShoppingAgentState = {
        "messages": create_current_turn_messages(),
    }

    assert generate_outfit(state) == {
        "outfit_recommendation": None,
    }


def test_generation_context_excludes_unavailable_and_hot_items() -> None:
    """验证模型看不到未干衣物和高温下的厚重单品。"""

    model = Mock(spec=BaseChatModel)
    structured_model = Mock()
    model.with_structured_output.return_value = structured_model
    structured_model.invoke.return_value = OutfitGenerationResult(outfit=None)
    messages = [
        HumanMessage(content="用我的衣橱搭配高温通勤服装"),
        ToolMessage(
            name="search_wardrobe",
            tool_call_id="wardrobe-filter-call",
            content=json.dumps(
                [
                    {
                        "wardrobe_item_id": "shirt-ready",
                        "name": "亚麻衬衫",
                        "status": "available",
                    },
                    {
                        "wardrobe_item_id": "shirt-drying",
                        "name": "棉衬衫",
                        "status": "unavailable",
                        "notes": "清洗后还没有晾干",
                    },
                    {
                        "wardrobe_item_id": "coat-heavy",
                        "name": "厚羊毛大衣",
                        "status": "available",
                    },
                ],
                ensure_ascii=False,
            ),
        ),
    ]
    generate_outfit = create_outfit_generation_node(model)

    generate_outfit(
        {
            "messages": messages,
            "weather_context": WeatherContext(
                location="上海",
                target_date="2026-08-02",
                temperature_max_c=35,
                source="user_provided",
            ),
        },
    )

    generation_message = structured_model.invoke.call_args.args[0][1]
    payload = json.loads(generation_message.content)
    candidate_ids = {record["wardrobe_item_id"] for record in payload["wardrobe_items"]}
    assert candidate_ids == {"shirt-ready"}


def test_generation_context_excludes_current_avoidances() -> None:
    """验证当前轮明确避雷项不会作为生成候选提供给模型。"""

    model = Mock(spec=BaseChatModel)
    structured_model = Mock()
    model.with_structured_output.return_value = structured_model
    structured_model.invoke.return_value = OutfitGenerationResult(
        outfit=None,
    )
    messages = [
        HumanMessage(content="不要黑色、羊毛和街头风"),
        ToolMessage(
            name="search_wardrobe",
            tool_call_id="wardrobe-avoidance-call",
            content=json.dumps(
                [
                    {
                        "wardrobe_item_id": "safe-shirt",
                        "name": "米白棉衬衫",
                        "colors": ["米白"],
                        "materials": ["棉"],
                        "style_tags": ["简约"],
                        "status": "available",
                    },
                    {
                        "wardrobe_item_id": "black-shirt",
                        "name": "深色衬衫",
                        "colors": ["黑色"],
                        "status": "available",
                    },
                    {
                        "wardrobe_item_id": "wool-shirt",
                        "name": "混纺衬衫",
                        "materials": ["羊毛混纺"],
                        "status": "available",
                    },
                    {
                        "wardrobe_item_id": "street-shirt",
                        "name": "印花衬衫",
                        "style_tags": ["街头风"],
                        "status": "available",
                    },
                ],
                ensure_ascii=False,
            ),
        ),
    ]
    generate_outfit = create_outfit_generation_node(model)

    generate_outfit(
        {
            "messages": messages,
            "requirement_analysis": (
                OutfitRequirementAnalysis(
                    intent=RequestIntent.OUTFIT,
                    avoided_colors=("黑色",),
                    avoided_materials=("羊毛",),
                    avoided_styles=("街头风",),
                )
            ),
        },
    )

    generation_message = structured_model.invoke.call_args.args[0][1]
    payload = json.loads(generation_message.content)
    assert [record["wardrobe_item_id"] for record in payload["wardrobe_items"]] == ["safe-shirt"]


def test_current_preference_overrides_profile_avoidance() -> None:
    """验证本轮主动选择黑色时不会沿用长期黑色避雷项。"""

    model = Mock(spec=BaseChatModel)
    structured_model = Mock()
    model.with_structured_output.return_value = structured_model
    structured_model.invoke.return_value = OutfitGenerationResult(
        outfit=None,
    )
    generate_outfit = create_outfit_generation_node(model)
    messages = [
        HumanMessage(content="这次我想穿黑色通勤服装"),
        ToolMessage(
            name="search_wardrobe",
            tool_call_id="profile-override-call",
            content=json.dumps(
                [
                    {
                        "wardrobe_item_id": "black-shirt",
                        "name": "黑色衬衫",
                        "colors": ["黑色"],
                        "status": "available",
                    },
                    {
                        "wardrobe_item_id": "white-shirt",
                        "name": "白色衬衫",
                        "colors": ["白色"],
                        "status": "available",
                    },
                ],
                ensure_ascii=False,
            ),
        ),
    ]

    generate_outfit(
        {
            "messages": messages,
            "requirement_analysis": (
                OutfitRequirementAnalysis(
                    intent=RequestIntent.OUTFIT,
                    color_preferences=("黑色",),
                )
            ),
            "style_profile_snapshot": (
                StyleProfileSnapshot(
                    avoided_colors=("黑色",),
                )
            ),
        },
    )

    generation_message = structured_model.invoke.call_args.args[0][1]
    payload = json.loads(generation_message.content)
    assert {record["wardrobe_item_id"] for record in payload["wardrobe_items"]} == {
        "black-shirt",
        "white-shirt",
    }
    assert payload["effective_style_constraints"]["preferred_colors"] == ["黑色"]
    assert payload["effective_style_constraints"]["avoided_colors"] == []
