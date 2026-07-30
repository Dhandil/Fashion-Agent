"""用户衣橱内存仓库测试。"""

import pytest

from app.db.repositories.in_memory_wardrobe import (
    InMemoryWardrobeRepository,
)
from app.domain.entities.wardrobe_item import (
    WardrobeItem,
    WardrobeItemStatus,
)


@pytest.mark.anyio
async def test_repository_filters_user_category_and_status() -> None:
    """验证衣橱查询的用户、品类和状态过滤。"""

    repository = InMemoryWardrobeRepository(
        items=[
            WardrobeItem(
                wardrobe_item_id="shirt-001",
                user_id="user-001",
                name="浅蓝色亚麻衬衫",
                category="衬衫",
                status="available",
            ),
            WardrobeItem(
                wardrobe_item_id="pants-001",
                user_id="user-001",
                name="黑色直筒西裤",
                category="长裤",
                status="laundry",
            ),
            WardrobeItem(
                wardrobe_item_id="shoes-001",
                user_id="user-001",
                name="黑色乐福鞋",
                category="鞋履",
                status="available",
            ),
            WardrobeItem(
                wardrobe_item_id="shirt-001",
                user_id="user-002",
                name="用户二的白色衬衫",
                category="衬衫",
                status="available",
            ),
        ],
    )

    # 不指定状态时返回用户一的全部衣物
    all_user_items = await repository.search(
        user_id="user-001",
    )
    assert len(all_user_items) == 3

    # 生成当天穿搭时只查询当前可用衣物
    available_items = await repository.search(
        user_id="user-001",
        status=WardrobeItemStatus.AVAILABLE,
    )
    assert {
        item.wardrobe_item_id
        for item in available_items
    } == {
        "shirt-001",
        "shoes-001",
    }

    # 清洗中的衣物可以被衣橱管理功能单独查询
    laundry_items = await repository.search(
        user_id="user-001",
        status=WardrobeItemStatus.LAUNDRY,
    )
    assert len(laundry_items) == 1
    assert (
        laundry_items[0].wardrobe_item_id
        == "pants-001"
    )

    # 品类和数量限制可以同时使用
    shirts = await repository.search(
        user_id="user-001",
        category="衬衫",
        limit=1,
    )
    assert len(shirts) == 1
    assert shirts[0].category == "衬衫"


@pytest.mark.anyio
async def test_repository_isolates_users_with_same_item_id() -> None:
    """验证相同单品 ID 不会跨用户覆盖或删除。"""

    user_one_item = WardrobeItem(
        wardrobe_item_id="shirt-001",
        user_id="user-001",
        name="用户一的衬衫",
        category="衬衫",
    )
    user_two_item = WardrobeItem(
        wardrobe_item_id="shirt-001",
        user_id="user-002",
        name="用户二的衬衫",
        category="衬衫",
    )

    repository = InMemoryWardrobeRepository(
        items=[
            user_one_item,
            user_two_item,
        ],
    )

    # 相同单品 ID 根据 user_id 返回不同对象
    assert (
        await repository.get_by_id(
            "user-001",
            "shirt-001",
        )
        == user_one_item
    )
    assert (
        await repository.get_by_id(
            "user-002",
            "shirt-001",
        )
        == user_two_item
    )

    # 删除用户一的衣物
    assert (
        await repository.delete(
            "user-001",
            "shirt-001",
        )
        is True
    )

    # 用户一的衣物已经不存在
    assert (
        await repository.get_by_id(
            "user-001",
            "shirt-001",
        )
        is None
    )

    # 用户二的同名单品仍然存在
    assert (
        await repository.get_by_id(
            "user-002",
            "shirt-001",
        )
        == user_two_item
    )