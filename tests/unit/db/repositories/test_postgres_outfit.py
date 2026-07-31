"""PostgreSQL 穿搭方案仓库测试。"""

from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.mappers.outfit import (
    outfit_entity_to_model,
)
from app.db.models.outfit import OutfitModel
from app.db.repositories.postgres_outfit import (
    PostgresOutfitRepository,
)
from app.domain.entities.outfit import (
    Outfit,
    OutfitItem,
    OutfitItemSource,
)


def create_test_outfit() -> Outfit:
    """创建多个测试可以复用的穿搭领域实体。"""

    return Outfit(
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
                reason="透气且适合通勤",
            ),
            OutfitItem(
                role="鞋履",
                name="白色运动鞋",
                source=OutfitItemSource.RECOMMENDATION,
                reason="让整体造型更加轻松",
            ),
        ),
        recommendation_reason=(
            "颜色清爽，并且适合炎热天气通勤。"
        ),
        is_favorite=True,
    )


@pytest.mark.anyio
async def test_postgres_outfit_repository_saves_outfit() -> None:
    """验证 PostgreSQL 仓库合并穿搭并刷新数据库会话。"""

    # 创建假的异步数据库 Session
    session = AsyncMock(spec=AsyncSession)

    repository = PostgresOutfitRepository(session)
    outfit = create_test_outfit()

    # 执行仓库保存操作
    saved_outfit = await repository.save(outfit)

    # merge 应该只调用一次
    session.merge.assert_awaited_once()

    # 取得实际传给 merge 的数据库模型
    merged_model = session.merge.await_args.args[0]

    assert isinstance(merged_model, OutfitModel)
    assert merged_model.user_id == "user-001"
    assert merged_model.outfit_id == "outfit-001"
    assert merged_model.style_tags == [
        "简约",
        "清爽",
    ]

    # 两个穿搭单品应该通过关系一起交给数据库
    assert len(merged_model.items) == 2
    assert merged_model.items[0].position == 0
    assert merged_model.items[1].position == 1

    # flush 应该只执行一次，但仓库不负责 commit
    session.flush.assert_awaited_once()
    session.commit.assert_not_awaited()

    # 仓库应该返回原始领域实体
    assert saved_outfit is outfit


@pytest.mark.anyio
async def test_postgres_outfit_repository_gets_outfit_by_id() -> None:
    """验证仓库按照用户 ID 和穿搭 ID 查询方案。"""

    session = AsyncMock(spec=AsyncSession)
    repository = PostgresOutfitRepository(session)

    # 模拟数据库中已经存在一套穿搭
    outfit_model = outfit_entity_to_model(
        create_test_outfit(),
    )

    # 模拟 execute() 返回的 SQLAlchemy 查询结果
    database_result = Mock()
    database_result.scalar_one_or_none.return_value = (
        outfit_model
    )
    session.execute.return_value = database_result

    # 执行查询
    found_outfit = await repository.get_by_id(
        user_id="user-001",
        outfit_id="outfit-001",
    )

    # 数据库查询应该只执行一次
    session.execute.assert_awaited_once()

    # 取得仓库实际构造的 SQLAlchemy 查询语句
    statement = session.execute.await_args.args[0]
    parameter_values = set(
        statement.compile().params.values(),
    )

    # SQL 查询必须同时包含用户 ID 和穿搭 ID
    assert "user-001" in parameter_values
    assert "outfit-001" in parameter_values

    # 数据库模型应该被恢复为领域实体
    assert found_outfit is not None
    assert found_outfit.user_id == "user-001"
    assert found_outfit.outfit_id == "outfit-001"
    assert found_outfit.items[0].name == (
        "浅蓝色亚麻衬衫"
    )
    assert (
        found_outfit.items[0].source
        is OutfitItemSource.WARDROBE
    )


@pytest.mark.anyio
async def test_postgres_outfit_repository_gets_outfits_by_ids() -> None:
    """验证仓库批量查询 Outfit 并恢复调用方要求的顺序。"""

    session = AsyncMock(spec=AsyncSession)
    repository = PostgresOutfitRepository(session)
    first_model = outfit_entity_to_model(
        create_test_outfit(),
    )
    second_model = outfit_entity_to_model(
        create_test_outfit().model_copy(
            update={
                "outfit_id": "outfit-002",
                "name": "第二套穿搭",
            },
        ),
    )
    scalar_result = Mock()
    scalar_result.all.return_value = [
        first_model,
        second_model,
    ]
    database_result = Mock()
    database_result.scalars.return_value = scalar_result
    session.execute.return_value = database_result

    outfits = await repository.get_by_ids(
        user_id="user-001",
        outfit_ids=(
            "outfit-002",
            "outfit-001",
        ),
    )

    session.execute.assert_awaited_once()
    assert [
        outfit.outfit_id
        for outfit in outfits
    ] == [
        "outfit-002",
        "outfit-001",
    ]


@pytest.mark.anyio
async def test_postgres_outfit_repository_searches_outfits() -> None:
    """验证仓库根据用户、场景和收藏状态查询穿搭。"""

    session = AsyncMock(spec=AsyncSession)
    repository = PostgresOutfitRepository(session)

    outfit_model = outfit_entity_to_model(
        create_test_outfit(),
    )

    # 模拟 result.scalars().all() 调用链
    scalar_result = Mock()
    scalar_result.all.return_value = [
        outfit_model,
    ]

    database_result = Mock()
    database_result.scalars.return_value = scalar_result
    session.execute.return_value = database_result

    # 只查询该用户收藏的通勤方案
    outfits = await repository.search(
        user_id="user-001",
        scenario="通勤",
        favorite_only=True,
        limit=10,
        offset=5,
    )

    session.execute.assert_awaited_once()

    # 检查查询语句中的绑定参数
    statement = session.execute.await_args.args[0]
    parameter_values = set(
        statement.compile().params.values(),
    )

    assert "user-001" in parameter_values
    assert "通勤" in parameter_values
    assert 10 in parameter_values
    assert 5 in parameter_values

    # 数据库模型应该被转换成领域实体列表
    assert len(outfits) == 1
    assert outfits[0].outfit_id == "outfit-001"
    assert outfits[0].scenario == "通勤"
    assert outfits[0].is_favorite is True


@pytest.mark.anyio
async def test_postgres_outfit_repository_counts_outfits() -> None:
    """验证仓库统计符合用户和过滤条件的记录数。"""

    session = AsyncMock(spec=AsyncSession)
    repository = PostgresOutfitRepository(session)

    database_result = Mock()
    database_result.scalar_one.return_value = 7
    session.execute.return_value = database_result

    count = await repository.count(
        user_id="user-001",
        scenario="通勤",
        favorite_only=True,
    )

    assert count == 7
    session.execute.assert_awaited_once()

    statement = session.execute.await_args.args[0]
    parameter_values = set(
        statement.compile().params.values(),
    )

    assert "user-001" in parameter_values
    assert "通勤" in parameter_values


@pytest.mark.anyio
async def test_postgres_outfit_repository_deletes_existing_outfit() -> None:
    """验证仓库能够删除存在的穿搭方案。"""

    session = AsyncMock(spec=AsyncSession)
    repository = PostgresOutfitRepository(session)

    outfit_model = outfit_entity_to_model(
        create_test_outfit(),
    )

    database_result = Mock()
    database_result.scalar_one_or_none.return_value = (
        outfit_model
    )
    session.execute.return_value = database_result

    deleted = await repository.delete(
        user_id="user-001",
        outfit_id="outfit-001",
    )

    # 找到记录后应该删除数据库模型
    session.delete.assert_awaited_once_with(
        outfit_model,
    )

    # 删除操作应该刷新到数据库事务中
    session.flush.assert_awaited_once()

    assert deleted is True


@pytest.mark.anyio
async def test_postgres_outfit_repository_does_not_delete_missing_outfit() -> None:
    """验证穿搭不存在时仓库返回 False。"""

    session = AsyncMock(spec=AsyncSession)
    repository = PostgresOutfitRepository(session)

    # 模拟数据库没有找到对应穿搭
    database_result = Mock()
    database_result.scalar_one_or_none.return_value = None
    session.execute.return_value = database_result

    deleted = await repository.delete(
        user_id="user-001",
        outfit_id="missing-outfit",
    )

    # 没有找到记录时不能执行删除和刷新
    session.delete.assert_not_awaited()
    session.flush.assert_not_awaited()

    assert deleted is False
