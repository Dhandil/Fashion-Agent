"""PostgreSQL 用户穿搭档案仓库测试。"""

from decimal import Decimal
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.mappers.style_profile import (
    style_profile_entity_to_model,
)
from app.db.models.style_profile import (
    StyleProfileModel,
)
from app.db.repositories.postgres_style_profile import (
    PostgresStyleProfileRepository,
)
from app.domain.entities.style_profile import (
    StyleProfile,
)


def create_test_style_profile() -> StyleProfile:
    """创建多个测试可以复用的用户穿搭档案。"""

    return StyleProfile(
        user_id="user-001",
        preferred_styles=(
            "简约",
            "通勤",
        ),
        avoided_styles=(
            "街头",
        ),
        preferred_colors=(
            "黑色",
            "浅蓝色",
        ),
        avoided_colors=(
            "亮黄色",
        ),
        preferred_fits=(
            "宽松",
        ),
        avoided_materials=(
            "粗糙羊毛",
        ),
        common_scenarios=(
            "通勤",
            "休闲",
        ),
        typical_budget_min=Decimal("200.00"),
        typical_budget_max=Decimal("500.00"),
        notes="通勤穿搭不要过于正式",
    )


@pytest.mark.anyio
async def test_postgres_style_profile_repository_saves_profile() -> None:
    """验证 PostgreSQL 仓库合并档案并刷新会话。"""

    session = AsyncMock(spec=AsyncSession)
    repository = PostgresStyleProfileRepository(
        session,
    )
    profile = create_test_style_profile()

    saved_profile = await repository.save(profile)

    # 保存时应该把领域实体转换成数据库模型
    session.merge.assert_awaited_once()
    merged_model = session.merge.await_args.args[0]

    assert isinstance(
        merged_model,
        StyleProfileModel,
    )
    assert merged_model.user_id == "user-001"
    assert merged_model.preferred_styles == [
        "简约",
        "通勤",
    ]
    assert merged_model.avoided_styles == [
        "街头",
    ]
    assert (
        merged_model.typical_budget_max
        == Decimal("500.00")
    )

    # 仓库刷新事务，但不负责提交事务
    session.flush.assert_awaited_once()
    session.commit.assert_not_awaited()

    assert saved_profile is profile


@pytest.mark.anyio
async def test_postgres_style_profile_repository_gets_profile() -> None:
    """验证仓库根据用户 ID 查询并恢复穿搭档案。"""

    session = AsyncMock(spec=AsyncSession)
    repository = PostgresStyleProfileRepository(
        session,
    )

    # 模拟数据库中已经存在的用户档案
    profile_model = style_profile_entity_to_model(
        create_test_style_profile(),
    )

    database_result = Mock()
    database_result.scalar_one_or_none.return_value = (
        profile_model
    )
    session.execute.return_value = database_result

    found_profile = await repository.get_by_user_id(
        "user-001",
    )

    session.execute.assert_awaited_once()

    # 检查 SQL 查询中是否包含当前用户 ID
    statement = session.execute.await_args.args[0]
    parameter_values = set(
        statement.compile().params.values(),
    )

    assert "user-001" in parameter_values

    # 数据库模型应该恢复成领域实体
    assert found_profile is not None
    assert found_profile.user_id == "user-001"
    assert found_profile.preferred_styles == (
        "简约",
        "通勤",
    )
    assert (
        found_profile.typical_budget_max
        == Decimal("500.00")
    )


@pytest.mark.anyio
async def test_postgres_style_profile_repository_deletes_profile() -> None:
    """验证仓库能够删除存在的用户穿搭档案。"""

    session = AsyncMock(spec=AsyncSession)
    repository = PostgresStyleProfileRepository(
        session,
    )

    profile_model = style_profile_entity_to_model(
        create_test_style_profile(),
    )

    database_result = Mock()
    database_result.scalar_one_or_none.return_value = (
        profile_model
    )
    session.execute.return_value = database_result

    deleted = await repository.delete_by_user_id(
        "user-001",
    )

    session.delete.assert_awaited_once_with(
        profile_model,
    )
    session.flush.assert_awaited_once()

    assert deleted is True


@pytest.mark.anyio
async def test_postgres_style_profile_repository_does_not_delete_missing_profile() -> None:
    """验证档案不存在时仓库返回 False。"""

    session = AsyncMock(spec=AsyncSession)
    repository = PostgresStyleProfileRepository(
        session,
    )

    database_result = Mock()
    database_result.scalar_one_or_none.return_value = None
    session.execute.return_value = database_result

    deleted = await repository.delete_by_user_id(
        "missing-user",
    )

    # 不存在的数据不能触发写操作
    session.delete.assert_not_awaited()
    session.flush.assert_not_awaited()

    assert deleted is False
