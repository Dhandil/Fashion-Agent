"""每轮对话状态准备节点测试。"""

from langchain_core.messages import HumanMessage

from app.agents.nodes.prepare_turn import (
    create_prepare_turn_node,
)
from app.agents.state.shopping import ShoppingAgentState
from app.domain.entities.outfit import (
    OutfitItem,
    OutfitRecommendation,
)


def create_previous_recommendation() -> OutfitRecommendation:
    """创建局部调整使用的上一套结构化推荐。"""

    return OutfitRecommendation(
        name="清爽通勤",
        scenario="通勤",
        items=(
            OutfitItem(
                role="上装",
                name="浅蓝色亚麻衬衫",
                source="wardrobe",
                source_reference_id="shirt-001",
            ),
        ),
        recommendation_reason="适合夏季通勤。",
    )


def test_prepare_turn_preserves_current_outfit_as_baseline() -> None:
    """验证上一轮 Outfit 被保存后再清空本轮输出。"""

    recommendation = create_previous_recommendation()
    node = create_prepare_turn_node()
    state: ShoppingAgentState = {
        "messages": [
            HumanMessage(
                content="把上衣换一件",
            ),
        ],
        "outfit_recommendation": recommendation,
    }

    result = node(state)

    assert result == {
        "outfit_recommendation": None,
        "tool_policy_rejection_count": 0,
        "knowledge_context": "",
        "knowledge_sources": [],
        "style_profile_context": "",
        "outfit_feedback_context": "",
        "recent_outfits_context": "",
        "previous_outfit_recommendation": (recommendation),
    }


def test_prepare_turn_keeps_existing_baseline_when_no_new_outfit() -> None:
    """验证普通知识轮次不会覆盖最近一次成功推荐。"""

    existing_baseline = create_previous_recommendation()
    node = create_prepare_turn_node()
    state: ShoppingAgentState = {
        "messages": [],
        "outfit_recommendation": None,
        "previous_outfit_recommendation": (existing_baseline),
    }

    result = node(state)

    assert result == {
        "outfit_recommendation": None,
        "tool_policy_rejection_count": 0,
        "knowledge_context": "",
        "knowledge_sources": [],
        "style_profile_context": "",
        "outfit_feedback_context": "",
        "recent_outfits_context": "",
    }


def test_prepare_turn_clears_previous_derived_context() -> None:
    """验证轻量路由不会复用上一轮的知识和个性化文本。"""

    node = create_prepare_turn_node()
    result = node(
        {
            "messages": [],
            "knowledge_context": "上一轮知识",
            "knowledge_sources": ["old-source.md"],
            "style_profile_context": "上一轮档案",
            "outfit_feedback_context": "上一轮反馈",
            "recent_outfits_context": "上一轮穿搭",
        },
    )

    assert result["knowledge_context"] == ""
    assert result["knowledge_sources"] == []
    assert result["style_profile_context"] == ""
    assert result["outfit_feedback_context"] == ""
    assert result["recent_outfits_context"] == ""
