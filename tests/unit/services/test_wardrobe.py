"""用户衣橱管理应用服务测试。"""

from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import WardrobeItemNotFoundError
from app.domain.entities.wardrobe_item import (
    WardrobeItem,
    WardrobeItemStatus,
)
from app.domain.repositories.wardrobe import (
    WardrobeRepository,
)
from app.services.wardrobe import (
    delete_wardrobe_item,
    get_wardrobe_item,
    list_wardrobe_items,
    update_wardrobe_item,
)


def create_test_item() -> WardrobeItem:
    """创建衣橱服务测试复用的领域实体。"""

    return WardrobeItem(
        wardrobe_item_id="wardrobe-001",
        user_id="user-001",
        name="浅蓝色亚麻衬衫",
        category="衬衫",
        colors=(
            "浅蓝色",
        ),
        status=WardrobeItemStatus.AVAILABLE,
        notes="原说明",
    )


@pytest.mark.anyio
async def test_list_wardrobe_items_returns_page() -> None:
    """验证列表服务同时读取当前页和匹配总数。"""

    repository = AsyncMock(
        spec=WardrobeRepository,
    )
    item = create_test_item()
    repository.search.return_value = [
        item,
    ]
    repository.count.return_value = 3

    page = await list_wardrobe_items(
        repository=repository,
        user_id="user-001",
        category="衬衫",
        status=WardrobeItemStatus.AVAILABLE,
        limit=1,
        offset=1,
    )

    assert page.items == (
        item,
    )
    assert page.total == 3
    repository.search.assert_awaited_once_with(
        user_id="user-001",
        category="衬衫",
        status=WardrobeItemStatus.AVAILABLE,
        limit=1,
        offset=1,
    )
    repository.count.assert_awaited_once_with(
        user_id="user-001",
        category="衬衫",
        status=WardrobeItemStatus.AVAILABLE,
    )


@pytest.mark.anyio
async def test_get_wardrobe_item_rejects_missing_item() -> None:
    """验证不存在或属于其他用户的衣物统一返回未找到。"""

    repository = AsyncMock(
        spec=WardrobeRepository,
    )
    repository.get_by_id.return_value = None

    with pytest.raises(
        WardrobeItemNotFoundError,
        match="未找到指定的衣橱单品",
    ):
        await get_wardrobe_item(
            repository=repository,
            user_id="user-001",
            wardrobe_item_id="missing-item",
        )


@pytest.mark.anyio
async def test_update_wardrobe_item_preserves_omitted_fields() -> None:
    """验证局部修改保留请求中没有提供的字段。"""

    repository = AsyncMock(
        spec=WardrobeRepository,
    )
    repository.get_by_id.return_value = (
        create_test_item()
    )
    repository.save.side_effect = (
        lambda item: item
    )

    item = await update_wardrobe_item(
        repository=repository,
        user_id="user-001",
        wardrobe_item_id="wardrobe-001",
        changes={
            "notes": "更新后的说明",
            "status": (
                WardrobeItemStatus.UNAVAILABLE
            ),
        },
    )

    assert item.name == "浅蓝色亚麻衬衫"
    assert item.colors == (
        "浅蓝色",
    )
    assert item.notes == "更新后的说明"
    assert (
        item.status
        is WardrobeItemStatus.UNAVAILABLE
    )
    repository.save.assert_awaited_once_with(item)


@pytest.mark.anyio
async def test_update_wardrobe_item_empty_changes_does_not_save() -> None:
    """验证空 PATCH 返回当前衣物且不产生写入。"""

    repository = AsyncMock(
        spec=WardrobeRepository,
    )
    current_item = create_test_item()
    repository.get_by_id.return_value = current_item

    item = await update_wardrobe_item(
        repository=repository,
        user_id="user-001",
        wardrobe_item_id="wardrobe-001",
        changes={},
    )

    assert item is current_item
    repository.save.assert_not_awaited()


@pytest.mark.anyio
async def test_delete_wardrobe_item_rejects_missing_item() -> None:
    """验证删除不存在的衣物时返回统一的未找到异常。"""

    repository = AsyncMock(
        spec=WardrobeRepository,
    )
    repository.delete.return_value = False

    with pytest.raises(
        WardrobeItemNotFoundError,
        match="未找到指定的衣橱单品",
    ):
        await delete_wardrobe_item(
            repository=repository,
            user_id="user-001",
            wardrobe_item_id="missing-item",
        )

