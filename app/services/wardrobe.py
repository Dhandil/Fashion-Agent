"""用户衣橱管理应用服务。"""

from dataclasses import dataclass

from app.core.exceptions import WardrobeItemNotFoundError
from app.domain.entities.wardrobe_item import (
    WardrobeItem,
    WardrobeItemStatus,
)
from app.domain.repositories.wardrobe import (
    WardrobeRepository,
)


@dataclass(
    frozen=True,
    slots=True,
)
class WardrobeItemPage:
    """一次衣橱分页查询的领域结果。"""

    items: tuple[WardrobeItem, ...]
    total: int


async def list_wardrobe_items(
    repository: WardrobeRepository,
    user_id: str,
    category: str | None = None,
    status: WardrobeItemStatus | None = None,
    limit: int = 50,
    offset: int = 0,
) -> WardrobeItemPage:
    """查询当前用户的一页衣橱单品和匹配总数。"""

    items = await repository.search(
        user_id=user_id,
        category=category,
        status=status,
        limit=limit,
        offset=offset,
    )
    total = await repository.count(
        user_id=user_id,
        category=category,
        status=status,
    )

    return WardrobeItemPage(
        items=tuple(items),
        total=total,
    )


async def get_wardrobe_item(
    repository: WardrobeRepository,
    user_id: str,
    wardrobe_item_id: str,
) -> WardrobeItem:
    """读取当前用户的一件衣橱单品。"""

    item = await repository.get_by_id(
        user_id=user_id,
        wardrobe_item_id=wardrobe_item_id,
    )

    if item is None:
        # 不区分不存在和属于其他用户，避免泄露衣橱数据
        raise WardrobeItemNotFoundError(
            "未找到指定的衣橱单品",
        )

    return item


async def update_wardrobe_item(
    repository: WardrobeRepository,
    user_id: str,
    wardrobe_item_id: str,
    changes: dict[str, object],
) -> WardrobeItem:
    """只更新用户明确提供的衣橱单品字段。"""

    item = await get_wardrobe_item(
        repository=repository,
        user_id=user_id,
        wardrobe_item_id=wardrobe_item_id,
    )

    if not changes:
        return item

    item_data = item.model_dump()
    item_data.update(changes)

    # 重新创建领域实体，确保修改后仍通过完整数据校验
    updated_item = WardrobeItem.model_validate(
        item_data,
    )

    return await repository.save(
        updated_item,
    )


async def delete_wardrobe_item(
    repository: WardrobeRepository,
    user_id: str,
    wardrobe_item_id: str,
) -> None:
    """删除当前用户的一件衣橱单品。"""

    deleted = await repository.delete(
        user_id=user_id,
        wardrobe_item_id=wardrobe_item_id,
    )

    if not deleted:
        raise WardrobeItemNotFoundError(
            "未找到指定的衣橱单品",
        )
