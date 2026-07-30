"""结构化穿搭推荐领域模型测试。"""

import pytest
from pydantic import ValidationError

from app.domain.entities.outfit import (
    OutfitItem,
    OutfitItemSource,
    OutfitRecommendation,
    WardrobeGap,
)


def test_outfit_recommendation_preserves_sources_and_gaps() -> None:
    """验证推荐能够区分已采用单品、替代项和衣橱缺口。"""

    recommendation = OutfitRecommendation(
        name="清爽夏季通勤",
        scenario="通勤",
        style_tags=[
            "简约",
            "清爽",
        ],
        season="夏季",
        items=[
            OutfitItem(
                role="上装",
                name="浅蓝色亚麻衬衫",
                source="wardrobe",
                source_reference_id="shirt-001",
                reason="透气且适合通勤",
            ),
            OutfitItem(
                role="下装",
                name="深灰色直筒西裤",
                source="wardrobe",
                source_reference_id="pants-001",
                reason="与浅蓝色搭配稳重但不沉闷",
            ),
            OutfitItem(
                role="鞋履",
                name="黑色简洁乐福鞋",
                source="recommendation",
                reason="补充通勤所需的利落鞋履",
            ),
        ],
        recommendation_reason=("浅蓝与深灰保持专业感，同时适合炎热天气。"),
        alternatives=[
            OutfitItem(
                role="下装",
                name="卡其色直筒裤",
                source="recommendation",
                reason="可以让整体风格更加轻松",
            ),
        ],
        wardrobe_gaps=[
            WardrobeGap(
                role="鞋履",
                suggested_item="黑色简洁乐福鞋",
                reason="当前衣橱结果中没有适合通勤的鞋履",
            ),
        ],
        notes="亚麻衬衫容易产生自然褶皱。",
    )

    # 列表输入统一转换为不可变元组
    assert recommendation.style_tags == (
        "简约",
        "清爽",
    )
    assert isinstance(recommendation.items, tuple)
    assert isinstance(recommendation.alternatives, tuple)
    assert isinstance(recommendation.wardrobe_gaps, tuple)

    # 已有衣物必须保留可追溯的衣橱单品 ID
    assert recommendation.items[0].source is OutfitItemSource.WARDROBE
    assert recommendation.items[0].source_reference_id == "shirt-001"

    # 缺口只是建议描述，不会伪装成真实商品
    assert recommendation.wardrobe_gaps[0].suggested_item == ("黑色简洁乐福鞋")

    # LLM 推荐模型不允许控制用户和数据库身份
    assert not hasattr(recommendation, "user_id")
    assert not hasattr(recommendation, "outfit_id")
    assert not hasattr(recommendation, "is_favorite")


def test_outfit_recommendation_requires_at_least_one_item() -> None:
    """验证完整穿搭推荐至少包含一个实际采用的单品。"""

    with pytest.raises(ValidationError):
        OutfitRecommendation(
            name="空搭配",
            scenario="通勤",
            items=[],
            recommendation_reason="没有可执行单品",
        )


def test_wardrobe_gap_requires_reason() -> None:
    """验证衣橱缺口必须解释为什么需要该单品。"""

    with pytest.raises(ValidationError):
        WardrobeGap(
            role="鞋履",
            suggested_item="黑色乐福鞋",
            reason="",
        )


def test_wardrobe_gap_must_match_recommended_outfit_item() -> None:
    """验证衣橱缺口不能变成与当前 Outfit 无关的购物清单。"""

    with pytest.raises(
        ValidationError,
        match="衣橱缺口必须对应搭配中的建议单品",
    ):
        OutfitRecommendation(
            name="夏季通勤",
            scenario="通勤",
            items=[
                OutfitItem(
                    role="上装",
                    name="浅蓝色亚麻衬衫",
                    source="wardrobe",
                    source_reference_id="shirt-001",
                ),
            ],
            recommendation_reason="使用已有衣物完成搭配。",
            wardrobe_gaps=[
                WardrobeGap(
                    role="鞋履",
                    suggested_item="黑色乐福鞋",
                    reason="适合通勤",
                ),
            ],
        )
