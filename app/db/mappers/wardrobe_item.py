"""衣橱单品数据库模型与领域实体转换。"""

from app.db.models.wardrobe_item import (
    WardrobeItemModel,
)
from app.domain.entities.wardrobe_item import (
    WardrobeItem,
    WardrobeItemStatus,
)


def wardrobe_item_entity_to_model(
    item: WardrobeItem,
) -> WardrobeItemModel:
    """将衣橱单品领域实体转换为数据库模型。"""

    return WardrobeItemModel(
        user_id=item.user_id,
        wardrobe_item_id=item.wardrobe_item_id,
        name=item.name,
        category=item.category,
        brand=item.brand,
        colors=list(item.colors),
        materials=list(item.materials),
        size=item.size,
        style_tags=list(item.style_tags),
        seasons=list(item.seasons),
        scenarios=list(item.scenarios),
        image_url=item.image_url,
        # 数据库保存枚举对应的字符串值
        status=item.status.value,
        notes=item.notes,
    )


def wardrobe_item_model_to_entity(
    item_model: WardrobeItemModel,
) -> WardrobeItem:
    """将衣橱单品数据库模型转换为领域实体。"""

    return WardrobeItem(
        user_id=item_model.user_id,
        wardrobe_item_id=(item_model.wardrobe_item_id),
        name=item_model.name,
        category=item_model.category,
        brand=item_model.brand,
        # 显式恢复成领域层使用的只读元组
        colors=tuple(item_model.colors),
        materials=tuple(item_model.materials),
        size=item_model.size,
        style_tags=tuple(item_model.style_tags),
        seasons=tuple(item_model.seasons),
        scenarios=tuple(item_model.scenarios),
        image_url=item_model.image_url,
        # 显式把数据库字符串恢复成领域枚举
        status=WardrobeItemStatus(
            item_model.status,
        ),
        notes=item_model.notes,
    )
