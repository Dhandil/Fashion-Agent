"""确定性 Outfit 局部修复测试。"""

from app.domain.entities.outfit import (
    OutfitItem,
    OutfitRecommendation,
)
from app.domain.policies.outfit_correction import (
    repair_hot_weather_wardrobe_items,
)
from app.domain.policies.wardrobe_candidates import (
    WardrobeCandidateExclusion,
    WardrobeCandidateExclusionReason,
    WardrobeCandidateSelection,
)


def _recommendation() -> OutfitRecommendation:
    """创建包含高温冲突上装的原方案。"""

    return OutfitRecommendation(
        name="高温通勤",
        scenario="高温通勤",
        items=(
            OutfitItem(
                role="上装",
                name="厚羊毛上衣",
                source="wardrobe",
                source_reference_id="upper-heavy",
            ),
            OutfitItem(
                role="下装",
                name="轻薄长裤",
                source="wardrobe",
                source_reference_id="lower-light",
            ),
            OutfitItem(
                role="鞋履",
                name="透气运动鞋",
                source="wardrobe",
                source_reference_id="shoes-light",
            ),
        ),
        recommendation_reason="适合通勤。",
    )


def test_repair_replaces_hot_item_with_same_category() -> None:
    """验证只替换冲突上装并保留下装和鞋履。"""

    records = (
        {
            "wardrobe_item_id": "upper-heavy",
            "name": "厚羊毛上衣",
            "category": "上装",
        },
        {
            "wardrobe_item_id": "upper-light",
            "name": "浅蓝轻薄棉衬衫",
            "category": "上装",
        },
    )
    selection = WardrobeCandidateSelection(
        eligible_records=(records[1],),
        exclusions=(
            WardrobeCandidateExclusion(
                wardrobe_item_id="upper-heavy",
                reason=(WardrobeCandidateExclusionReason.HOT_WEATHER_CONFLICT),
            ),
        ),
    )

    repaired = repair_hot_weather_wardrobe_items(
        _recommendation(),
        wardrobe_records=records,
        selection=selection,
    )

    assert repaired is not None
    assert repaired.items[0].source_reference_id == (
        "upper-light"
    )
    assert repaired.items[0].name == "浅蓝轻薄棉衬衫"
    assert repaired.items[1:] == _recommendation().items[1:]


def test_repair_returns_none_without_same_category_candidate() -> None:
    """验证没有真实同品类替代时继续使用原安全拒绝流程。"""

    selection = WardrobeCandidateSelection(
        eligible_records=(),
        exclusions=(
            WardrobeCandidateExclusion(
                wardrobe_item_id="upper-heavy",
                reason=(WardrobeCandidateExclusionReason.HOT_WEATHER_CONFLICT),
            ),
        ),
    )

    repaired = repair_hot_weather_wardrobe_items(
        _recommendation(),
        wardrobe_records=(),
        selection=selection,
    )

    assert repaired is None
