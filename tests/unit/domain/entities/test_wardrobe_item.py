"""用户衣橱单品领域实体测试。"""

import pytest
from pydantic import ValidationError

from app.domain.entities.wardrobe_item import (
    WardrobeItem,
    WardrobeItemStatus,
)


def test_wardrobe_item_converts_collection_fields() -> None:
    """验证衣橱单品的列表输入会转换为元组。"""

    item = WardrobeItem(
        wardrobe_item_id="wardrobe-001",
        user_id="user-001",
        name="浅蓝色亚麻衬衫",
        category="衬衫",
        colors=[
            "浅蓝色",
        ],
        materials=[
            "亚麻",
            "棉",
        ],
        style_tags=[
            "简约",
            "通勤",
        ],
        seasons=[
            "夏季",
        ],
        scenarios=[
            "通勤",
            "休闲",
        ],
    )

    assert item.colors == (
        "浅蓝色",
    )
    assert item.materials == (
        "亚麻",
        "棉",
    )
    assert item.style_tags == (
        "简约",
        "通勤",
    )
    assert item.seasons == (
        "夏季",
    )
    assert item.scenarios == (
        "通勤",
        "休闲",
    )


def test_wardrobe_item_uses_available_default_status() -> None:
    """验证新录入衣物默认处于可用状态。"""

    item = WardrobeItem(
        wardrobe_item_id="wardrobe-001",
        user_id="user-001",
        name="黑色直筒西裤",
        category="长裤",
    )

    assert item.status is WardrobeItemStatus.AVAILABLE
    assert item.brand is None
    assert item.size is None
    assert item.image_url is None


def test_wardrobe_item_accepts_string_status() -> None:
    """验证 Pydantic 能将状态字符串转换为枚举。"""

    item = WardrobeItem(
        wardrobe_item_id="wardrobe-001",
        user_id="user-001",
        name="白色棉质衬衫",
        category="衬衫",
        status="laundry",
    )

    assert item.status is WardrobeItemStatus.LAUNDRY


def test_wardrobe_item_rejects_unknown_status() -> None:
    """验证未知衣物状态会被拒绝。"""

    with pytest.raises(ValidationError):
        WardrobeItem(
            wardrobe_item_id="wardrobe-001",
            user_id="user-001",
            name="白色棉质衬衫",
            category="衬衫",
            status="lost",
        )