"""衣橱单品数据库转换测试。"""

from app.db.mappers.wardrobe_item import (
    wardrobe_item_entity_to_model,
    wardrobe_item_model_to_entity,
)
from app.domain.entities.wardrobe_item import (
    WardrobeItem,
    WardrobeItemStatus,
)


def test_wardrobe_item_mapper_preserves_item_data() -> None:
    """验证衣橱单品双向转换后数据保持一致。"""

    item = WardrobeItem(
        wardrobe_item_id="wardrobe-001",
        user_id="user-001",
        name="浅蓝色亚麻衬衫",
        category="衬衫",
        brand="示例品牌",
        colors=(
            "浅蓝色",
            "白色",
        ),
        materials=(
            "亚麻",
            "棉",
        ),
        size="M",
        style_tags=(
            "简约",
            "通勤",
        ),
        seasons=("夏季",),
        scenarios=(
            "通勤",
            "休闲",
        ),
        image_url="images/wardrobe-001.jpg",
        status=WardrobeItemStatus.UNAVAILABLE,
        notes="需要低温清洗",
    )

    # 模拟写入数据库前的转换
    item_model = wardrobe_item_entity_to_model(
        item,
    )

    # JSON 字段应该使用列表
    assert item_model.colors == [
        "浅蓝色",
        "白色",
    ]
    assert item_model.materials == [
        "亚麻",
        "棉",
    ]
    assert item_model.style_tags == [
        "简约",
        "通勤",
    ]

    # 枚举在数据库中保存为字符串
    assert item_model.status == "unavailable"

    # 模拟从数据库读取后的转换
    restored_item = wardrobe_item_model_to_entity(
        item_model,
    )

    # 全部领域数据应该保持一致
    assert restored_item == item

    # 状态字符串应该恢复为领域枚举
    assert restored_item.status is WardrobeItemStatus.UNAVAILABLE

    # JSON 列表应该恢复为元组
    assert restored_item.scenarios == (
        "通勤",
        "休闲",
    )
