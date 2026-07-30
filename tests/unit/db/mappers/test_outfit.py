"""穿搭方案数据库转换测试。"""

from app.db.mappers.outfit import (
    outfit_entity_to_model,
    outfit_model_to_entity,
)
from app.domain.entities.outfit import (
    Outfit,
    OutfitItem,
    OutfitItemSource,
)


def test_outfit_mapper_preserves_outfit_data() -> None:
    """验证穿搭方案双向转换后数据和单品顺序保持一致。"""

    # 创建业务层使用的完整穿搭方案
    outfit = Outfit(
        outfit_id="outfit-001",
        user_id="user-001",
        name="夏季通勤穿搭",
        scenario="通勤",
        style_tags=(
            "简约",
            "清爽",
        ),
        season="夏季",
        items=(
            OutfitItem(
                role="上装",
                name="浅蓝色亚麻衬衫",
                source=OutfitItemSource.WARDROBE,
                source_reference_id="wardrobe-001",
                reason="透气且适合通勤场景",
            ),
            OutfitItem(
                role="鞋履",
                name="白色简约运动鞋",
                source=OutfitItemSource.RECOMMENDATION,
                reason="让整体穿搭更轻松",
            ),
        ),
        recommendation_reason=(
            "整体配色清爽，适合夏季日常通勤。"
        ),
        notes="下雨时可以把运动鞋换成防水鞋。",
        is_favorite=True,
    )

    # 模拟保存到数据库之前的转换
    outfit_model = outfit_entity_to_model(outfit)

    # 元组应该被转换为数据库 JSON 字段使用的列表
    assert outfit_model.style_tags == [
        "简约",
        "清爽",
    ]

    # 单品位置应该按照原始顺序生成
    assert [
        item.position
        for item in outfit_model.items
    ] == [0, 1]

    # 枚举应该转换为数据库保存的字符串
    assert outfit_model.items[0].source == "wardrobe"
    assert outfit_model.items[1].source == "recommendation"

    # 子表记录应该继承所属穿搭和用户的 ID
    assert outfit_model.items[0].user_id == "user-001"
    assert outfit_model.items[0].outfit_id == "outfit-001"

    # 模拟从数据库读取后转换回领域实体
    restored_outfit = outfit_model_to_entity(
        outfit_model,
    )

    # 完整领域数据应该保持一致
    assert restored_outfit == outfit

    # 数据库列表应该恢复为不可变元组
    assert restored_outfit.style_tags == (
        "简约",
        "清爽",
    )

    # 数据库字符串应该恢复成领域枚举
    assert (
        restored_outfit.items[0].source
        is OutfitItemSource.WARDROBE
    )