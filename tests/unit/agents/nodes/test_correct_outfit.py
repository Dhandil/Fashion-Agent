"""Outfit 单次受限修正节点测试。"""

import json
from unittest.mock import Mock

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, ToolMessage

from app.agents.nodes.correct_outfit import (
    create_outfit_correction_node,
)
from app.agents.schemas.outfit import OutfitGenerationResult
from app.agents.schemas.requirements import (
    OutfitRequirementAnalysis,
    RequestIntent,
)
from app.agents.schemas.style_profile import (
    StyleProfileSnapshot,
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
from app.domain.entities.weather import WeatherContext


def _original_outfit() -> OutfitRecommendation:
    """创建缺少下装和鞋履的原方案。"""

    return OutfitRecommendation(
        name="不完整通勤方案",
        scenario="通勤",
        items=(
            OutfitItem(
                role="上装",
                name="亚麻衬衫",
                source="wardrobe",
                source_reference_id="upper-001",
            ),
        ),
        recommendation_reason="目前只有上装。",
    )


def _corrected_outfit() -> OutfitRecommendation:
    """创建补齐核心角色且仅引用真实衣橱 ID 的方案。"""

    return OutfitRecommendation(
        name="完整通勤方案",
        scenario="通勤",
        items=(
            OutfitItem(
                role="上装",
                name="亚麻衬衫",
                source="wardrobe",
                source_reference_id="upper-001",
            ),
            OutfitItem(
                role="下装",
                name="直筒长裤",
                source="wardrobe",
                source_reference_id="lower-001",
            ),
            OutfitItem(
                role="鞋履",
                name="乐福鞋",
                source="wardrobe",
                source_reference_id="shoes-001",
            ),
        ),
        recommendation_reason="补齐通勤所需核心单品。",
    )


def _invalid_state() -> dict:
    """创建包含原方案、问题和当前轮真实工具证据的状态。"""

    wardrobe_records = [
        {
            "wardrobe_item_id": item_id,
            "name": name,
            "status": "available",
        }
        for item_id, name in (
            ("upper-001", "亚麻衬衫"),
            ("lower-001", "直筒长裤"),
            ("shoes-001", "乐福鞋"),
        )
    ]
    return {
        "messages": [
            HumanMessage(content="用我的衣橱搭配通勤服装"),
            ToolMessage(
                name="search_wardrobe",
                tool_call_id="wardrobe-call-1",
                content=json.dumps(
                    wardrobe_records,
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
        "outfit_recommendation": _original_outfit(),
        "outfit_feasibility_report": (
            OutfitFeasibilityReport(
                is_executable=False,
                issues=(
                    OutfitFeasibilityIssue(
                        code=(OutfitIssueCode.MISSING_CORE_ROLE),
                        severity=OutfitIssueSeverity.ERROR,
                        message="完整穿搭缺少下装和鞋履。",
                    ),
                ),
            )
        ),
        "outfit_correction_attempts": 0,
    }


def test_correction_uses_current_evidence_once() -> None:
    """验证修正模型收到真实证据并返回一次候选方案。"""

    model = Mock(spec=BaseChatModel)
    structured_model = Mock()
    model.with_structured_output.return_value = structured_model
    corrected = _corrected_outfit()
    structured_model.invoke.return_value = OutfitGenerationResult(outfit=corrected)
    node = create_outfit_correction_node(model)

    result = node(_invalid_state())

    assert result["outfit_recommendation"] == corrected
    assert result["outfit_correction_attempts"] == 1
    correction_message = structured_model.invoke.call_args.args[0][1]
    assert "missing_core_role" in correction_message.content
    assert "lower-001" in correction_message.content
    assert "shoes-001" in correction_message.content


def test_correction_failure_keeps_original_for_final_check() -> None:
    """验证供应商失败时不会丢失原错误及最终拒绝依据。"""

    model = Mock(spec=BaseChatModel)
    structured_model = Mock()
    model.with_structured_output.return_value = structured_model
    structured_model.invoke.side_effect = RuntimeError(
        "provider unavailable",
    )
    node = create_outfit_correction_node(model)
    state = _invalid_state()

    result = node(state)

    assert result["outfit_recommendation"] == (state["outfit_recommendation"])
    assert result["outfit_correction_attempts"] == 1


def test_correction_context_uses_only_eligible_wardrobe_items() -> None:
    """验证修正同样不能重新选中未干或高温冲突衣物。"""

    model = Mock(spec=BaseChatModel)
    structured_model = Mock()
    model.with_structured_output.return_value = structured_model
    structured_model.invoke.return_value = OutfitGenerationResult(
        outfit=_corrected_outfit(),
    )
    state = _invalid_state()
    wardrobe_message = state["messages"][1]
    wardrobe_message.content = json.dumps(
        [
            {
                "wardrobe_item_id": "upper-001",
                "name": "亚麻衬衫",
                "status": "available",
            },
            {
                "wardrobe_item_id": "lower-001",
                "name": "直筒长裤",
                "status": "available",
            },
            {
                "wardrobe_item_id": "shoes-001",
                "name": "乐福鞋",
                "status": "available",
            },
            {
                "wardrobe_item_id": "shirt-drying",
                "name": "棉衬衫",
                "status": "unavailable",
                "notes": "尚未晾干",
            },
            {
                "wardrobe_item_id": "coat-heavy",
                "name": "厚羊毛大衣",
                "status": "available",
            },
            {
                "wardrobe_item_id": "shirt-black",
                "name": "黑色衬衫",
                "colors": ["黑色"],
                "status": "available",
            },
            {
                "wardrobe_item_id": "shirt-neon",
                "name": "荧光色衬衫",
                "colors": ["荧光色"],
                "status": "available",
            },
        ],
        ensure_ascii=False,
    )
    state["requirement_analysis"] = OutfitRequirementAnalysis(
        intent=RequestIntent.OUTFIT,
        scenario="通勤",
        needs_wardrobe=True,
        avoided_colors=("黑色",),
    )
    state["style_profile_snapshot"] = StyleProfileSnapshot(
        avoided_colors=("荧光色",),
    )
    state["weather_context"] = WeatherContext(
        location="上海",
        target_date="2026-08-02",
        temperature_max_c=35,
        source="user_provided",
    )
    node = create_outfit_correction_node(model)

    node(state)

    correction_message = structured_model.invoke.call_args.args[0][1]
    payload = json.loads(correction_message.content)
    candidate_ids = {record["wardrobe_item_id"] for record in payload["wardrobe_items"]}
    assert candidate_ids == {
        "upper-001",
        "lower-001",
        "shoes-001",
    }
