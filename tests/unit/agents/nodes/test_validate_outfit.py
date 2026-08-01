"""Outfit 可执行性检查节点测试。"""

import json

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    ToolMessage,
)

from app.agents.nodes.validate_outfit import validate_outfit
from app.agents.schemas.requirements import (
    OutfitRequirementAnalysis,
    RequestIntent,
)
from app.domain.entities.outfit import (
    OutfitItem,
    OutfitRecommendation,
)
from app.domain.entities.outfit_validation import (
    OutfitIssueCode,
)


def _recommendation() -> OutfitRecommendation:
    """创建引用当前轮衣橱单品的完整推荐。"""

    return OutfitRecommendation(
        name="夏季通勤",
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
        recommendation_reason="适合夏季通勤。",
    )


def _state_with_wardrobe_records(
    records: list[dict[str, str]],
) -> dict:
    """创建包含当前轮衣橱 ToolMessage 的状态。"""

    return {
        "messages": [
            HumanMessage(content="用我的衣橱搭配通勤服装"),
            ToolMessage(
                name="search_wardrobe",
                tool_call_id="wardrobe-call-1",
                content=json.dumps(
                    records,
                    ensure_ascii=False,
                ),
            ),
            AIMessage(content="已生成一套通勤搭配。"),
        ],
        "requirement_analysis": (
            OutfitRequirementAnalysis(
                intent=RequestIntent.OUTFIT,
                scenario="通勤",
                needs_wardrobe=True,
            )
        ),
        "outfit_recommendation": _recommendation(),
    }


def test_validate_outfit_keeps_executable_recommendation() -> None:
    """验证真实且完整的推荐不会被清空。"""

    result = validate_outfit(
        _state_with_wardrobe_records(
            [
                {
                    "wardrobe_item_id": item_id,
                    "status": "available",
                }
                for item_id in (
                    "upper-001",
                    "lower-001",
                    "shoes-001",
                )
            ],
        ),
    )

    report = result["outfit_feasibility_report"]
    assert report.is_executable is True
    assert "outfit_recommendation" not in result


def test_validate_outfit_blocks_unknown_sources() -> None:
    """验证修正后来源仍无效时清空推荐并返回原因消息。"""

    state = _state_with_wardrobe_records([])
    state["outfit_correction_attempts"] = 1
    result = validate_outfit(state)

    report = result["outfit_feasibility_report"]
    assert report.is_executable is False
    assert result["outfit_recommendation"] is None
    assert any(issue.code is OutfitIssueCode.UNKNOWN_SOURCE_ID for issue in report.issues)
    assert "没有通过可执行性检查" in (result["messages"][0].content)


def test_first_validation_failure_waits_for_correction() -> None:
    """验证首次失败保留候选方案，不提前生成最终失败回复。"""

    result = validate_outfit(
        _state_with_wardrobe_records([]),
    )

    report = result["outfit_feasibility_report"]
    assert report.is_executable is False
    assert "outfit_recommendation" not in result
    assert "messages" not in result
