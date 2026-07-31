"""穿搭方案领域实体测试。"""

import pytest
from pydantic import ValidationError

from app.domain.entities.outfit import (
    Outfit,
    OutfitItem,
    OutfitItemSource,
)


def test_outfit_contains_wardrobe_and_recommended_items() -> None:
    """验证穿搭可以组合已有衣物和通用建议。"""

    outfit = Outfit(
        outfit_id="outfit-001",
        user_id="user-001",
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
                source_reference_id="wardrobe-001",
                reason="透气并且适合通勤",
            ),
            OutfitItem(
                role="下装",
                name="深灰色直筒西裤",
                source="recommendation",
                reason="与浅蓝色搭配稳重但不沉闷",
            ),
        ],
        recommendation_reason=("浅蓝与深灰保持专业感，同时适合炎热天气。"),
    )

    # 列表输入应该转换为不可变元组
    assert outfit.style_tags == (
        "简约",
        "清爽",
    )
    assert isinstance(outfit.items, tuple)

    # 第一件单品来自用户衣橱
    assert outfit.items[0].source is OutfitItemSource.WARDROBE
    assert outfit.items[0].source_reference_id == "wardrobe-001"

    # 通用建议不需要伪造来源 ID
    assert outfit.items[1].source is OutfitItemSource.RECOMMENDATION
    assert outfit.items[1].source_reference_id is None

    # 新穿搭默认没有被收藏
    assert outfit.is_favorite is False


@pytest.mark.parametrize(
    "source",
    [
        OutfitItemSource.WARDROBE,
        OutfitItemSource.PRODUCT,
    ],
)
def test_outfit_item_requires_real_source_id(
    source: OutfitItemSource,
) -> None:
    """验证衣橱和商品单品必须能够追溯来源。"""

    with pytest.raises(
        ValidationError,
        match="必须提供来源 ID",
    ):
        OutfitItem(
            role="上装",
            name="白色衬衫",
            source=source,
        )


def test_recommended_item_does_not_require_source_id() -> None:
    """验证通用穿搭建议可以不关联具体数据。"""

    item = OutfitItem(
        role="鞋履",
        name="黑色简洁乐福鞋",
        source=OutfitItemSource.RECOMMENDATION,
    )

    assert item.source_reference_id is None


def test_recommended_item_rejects_source_id() -> None:
    """验证通用建议不能伪装成可追溯衣物或商品。"""

    with pytest.raises(
        ValidationError,
        match="通用建议单品不能提供来源 ID",
    ):
        OutfitItem(
            role="鞋履",
            name="黑色乐福鞋",
            source=OutfitItemSource.RECOMMENDATION,
            source_reference_id="invented-id",
        )


def test_outfit_rejects_empty_items() -> None:
    """验证完整穿搭方案不能没有任何单品。"""

    with pytest.raises(ValidationError):
        Outfit(
            outfit_id="outfit-001",
            user_id="user-001",
            name="空搭配",
            scenario="通勤",
            items=[],
            recommendation_reason="测试",
        )
