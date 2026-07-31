"""PostgreSQL 用户衣橱仓库测试。"""

from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.mappers.wardrobe_item import (
    wardrobe_item_entity_to_model,
)
from app.db.models.wardrobe_item import (
    WardrobeItemModel,
)
from app.db.repositories.postgres_wardrobe import (
    PostgresWardrobeRepository,
)
from app.domain.entities.wardrobe_item import (
    WardrobeItem,
    WardrobeItemStatus,
)


def create_test_wardrobe_item() -> WardrobeItem:
    """创建多个测试可以复用的衣橱单品。"""

    return WardrobeItem(
        wardrobe_item_id="wardrobe-001",
        user_id="user-001",
        name="浅蓝色亚麻衬衫",
        category="衬衫",
        brand="示例品牌",
        colors=(
            "浅蓝色",
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
        seasons=(
            "夏季",
        ),
        scenarios=(
            "通勤",
            "休闲",
        ),
        image_url="images/wardrobe-001.jpg",
        status=WardrobeItemStatus.AVAILABLE,
        notes="低温清洗",
    )


@pytest.mark.anyio
async def test_postgres_wardrobe_repository_saves_item() -> None:
    """验证 PostgreSQL 仓库合并衣物并刷新会话。"""

    session = AsyncMock(spec=AsyncSession)
    repository = PostgresWardrobeRepository(session)
    item = create_test_wardrobe_item()

    saved_item = await repository.save(item)

    session.merge.assert_awaited_once()
    merged_model = session.merge.await_args.args[0]

    # 领域实体应该转换为数据库模型
    assert isinstance(
        merged_model,
        WardrobeItemModel,
    )
    assert merged_model.user_id == "user-001"
    assert (
        merged_model.wardrobe_item_id
        == "wardrobe-001"
    )
    assert merged_model.materials == [
        "亚麻",
        "棉",
    ]

    # 枚举在数据库中保存为字符串
    assert merged_model.status == "available"

    # 仓库刷新变更，但不自行提交事务
    session.flush.assert_awaited_once()
    session.commit.assert_not_awaited()

    assert saved_item is item


@pytest.mark.anyio
async def test_postgres_wardrobe_repository_gets_item_by_id() -> None:
    """验证仓库按照用户 ID 和衣物 ID 查询单品。"""

    session = AsyncMock(spec=AsyncSession)
    repository = PostgresWardrobeRepository(session)

    item_model = wardrobe_item_entity_to_model(
        create_test_wardrobe_item(),
    )

    database_result = Mock()
    database_result.scalar_one_or_none.return_value = (
        item_model
    )
    session.execute.return_value = database_result

    found_item = await repository.get_by_id(
        user_id="user-001",
        wardrobe_item_id="wardrobe-001",
    )

    session.execute.assert_awaited_once()

    # 查询必须同时包含用户 ID 和衣物 ID
    statement = session.execute.await_args.args[0]
    parameter_values = set(
        statement.compile().params.values(),
    )

    assert "user-001" in parameter_values
    assert "wardrobe-001" in parameter_values

    # 数据库模型应该恢复成领域实体
    assert found_item is not None
    assert found_item.name == "浅蓝色亚麻衬衫"
    assert found_item.materials == (
        "亚麻",
        "棉",
    )
    assert (
        found_item.status
        is WardrobeItemStatus.AVAILABLE
    )


@pytest.mark.anyio
async def test_postgres_wardrobe_repository_searches_available_items() -> None:
    """验证仓库按照用户、品类和可穿状态筛选衣物。"""

    session = AsyncMock(spec=AsyncSession)
    repository = PostgresWardrobeRepository(session)

    item_model = wardrobe_item_entity_to_model(
        create_test_wardrobe_item(),
    )

    # 模拟 result.scalars().all() 调用链
    scalar_result = Mock()
    scalar_result.all.return_value = [
        item_model,
    ]

    database_result = Mock()
    database_result.scalars.return_value = scalar_result
    session.execute.return_value = database_result

    items = await repository.search(
        user_id="user-001",
        category="衬衫",
        status=WardrobeItemStatus.AVAILABLE,
        limit=20,
        offset=10,
    )

    session.execute.assert_awaited_once()

    # 验证查询语句包含用户、品类、状态和数量限制
    statement = session.execute.await_args.args[0]
    parameter_values = set(
        statement.compile().params.values(),
    )

    assert "user-001" in parameter_values
    assert "衬衫" in parameter_values
    assert "available" in parameter_values
    assert 20 in parameter_values
    assert 10 in parameter_values

    # 查询结果应该转换为领域实体
    assert len(items) == 1
    assert items[0].user_id == "user-001"
    assert items[0].category == "衬衫"
    assert (
        items[0].status
        is WardrobeItemStatus.AVAILABLE
    )


@pytest.mark.anyio
async def test_postgres_wardrobe_repository_counts_filtered_items() -> None:
    """验证仓库在数据库中统计当前用户的匹配衣物。"""

    session = AsyncMock(spec=AsyncSession)
    repository = PostgresWardrobeRepository(session)

    database_result = Mock()
    database_result.scalar_one.return_value = 4
    session.execute.return_value = database_result

    total = await repository.count(
        user_id="user-001",
        category="衬衫",
        status=WardrobeItemStatus.AVAILABLE,
    )

    statement = session.execute.await_args.args[0]
    parameter_values = set(
        statement.compile().params.values(),
    )

    assert "user-001" in parameter_values
    assert "衬衫" in parameter_values
    assert "available" in parameter_values
    assert total == 4


@pytest.mark.anyio
async def test_postgres_wardrobe_repository_deletes_existing_item() -> None:
    """验证仓库能够删除存在的衣橱单品。"""

    session = AsyncMock(spec=AsyncSession)
    repository = PostgresWardrobeRepository(session)

    item_model = wardrobe_item_entity_to_model(
        create_test_wardrobe_item(),
    )

    database_result = Mock()
    database_result.scalar_one_or_none.return_value = (
        item_model
    )
    session.execute.return_value = database_result

    deleted = await repository.delete(
        user_id="user-001",
        wardrobe_item_id="wardrobe-001",
    )

    session.delete.assert_awaited_once_with(
        item_model,
    )
    session.flush.assert_awaited_once()

    assert deleted is True


@pytest.mark.anyio
async def test_postgres_wardrobe_repository_does_not_delete_missing_item() -> None:
    """验证衣橱单品不存在时仓库返回 False。"""

    session = AsyncMock(spec=AsyncSession)
    repository = PostgresWardrobeRepository(session)

    database_result = Mock()
    database_result.scalar_one_or_none.return_value = None
    session.execute.return_value = database_result

    deleted = await repository.delete(
        user_id="user-001",
        wardrobe_item_id="missing-item",
    )

    # 没有查询到衣物时不能执行数据库写操作
    session.delete.assert_not_awaited()
    session.flush.assert_not_awaited()

    assert deleted is False
