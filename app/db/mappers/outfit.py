"""穿搭方案领域实体与数据库模型之间的转换。"""

from app.db.models.outfit import (
    OutfitItemModel,
    OutfitModel,
)
from app.domain.entities.outfit import (
    Outfit,
    OutfitItem,
    OutfitItemSource,
)


def outfit_entity_to_model(outfit: Outfit) -> OutfitModel:
    """把穿搭领域实体转换为 SQLAlchemy 数据库模型。"""

    # enumerate 会同时提供单品的位置和单品对象
    # position 用于保存单品在整套穿搭中的排列顺序
    item_models = [
        OutfitItemModel(
            user_id=outfit.user_id,
            outfit_id=outfit.outfit_id,
            position=position,
            role=item.role,
            name=item.name,
            source=item.source.value,
            source_reference_id=item.source_reference_id,
            reason=item.reason,
        )
        for position, item in enumerate(outfit.items)
    ]

    # 将元组转换为列表，方便保存到 JSON 字段
    return OutfitModel(
        user_id=outfit.user_id,
        outfit_id=outfit.outfit_id,
        name=outfit.name,
        scenario=outfit.scenario,
        style_tags=list(outfit.style_tags),
        season=outfit.season,
        recommendation_reason=outfit.recommendation_reason,
        notes=outfit.notes,
        is_favorite=outfit.is_favorite,
        items=item_models,
    )


def outfit_model_to_entity(model: OutfitModel) -> Outfit:
    """把 SQLAlchemy 数据库模型转换为穿搭领域实体。"""

    # 数据库查询结果不一定天然保持顺序
    # 因此按照 position 明确排序
    ordered_items = sorted(
        model.items,
        key=lambda item: item.position,
    )

    # 把数据库中的单品模型转换为领域单品
    outfit_items = tuple(
        OutfitItem(
            role=item.role,
            name=item.name,
            source=OutfitItemSource(item.source),
            source_reference_id=item.source_reference_id,
            reason=item.reason,
        )
        for item in ordered_items
    )

    # 将数据库 JSON 列表重新转换为不可变元组
    return Outfit(
        user_id=model.user_id,
        outfit_id=model.outfit_id,
        name=model.name,
        scenario=model.scenario,
        style_tags=tuple(model.style_tags),
        season=model.season,
        items=outfit_items,
        recommendation_reason=model.recommendation_reason,
        notes=model.notes,
        is_favorite=model.is_favorite,
    )