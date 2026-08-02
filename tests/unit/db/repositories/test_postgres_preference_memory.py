"""长期偏好审计 PostgreSQL 仓库测试。"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.mappers.preference_memory import (
    preference_memory_entity_to_model,
)
from app.db.models.preference_memory import (
    PreferenceMemoryModel,
)
from app.db.repositories.postgres_preference_memory import (
    PostgresPreferenceMemoryRepository,
)
from app.domain.entities.preference_candidate import (
    PreferenceCandidateCategory,
    PreferenceDirection,
)
from app.domain.entities.preference_memory import (
    PreferenceMemory,
    PreferenceMemorySource,
)


def _memory() -> PreferenceMemory:
    """创建 PostgreSQL 仓库测试记录。"""

    confirmed_at = datetime(
        2026,
        8,
        2,
        10,
        tzinfo=UTC,
    )
    return PreferenceMemory(
        preference_memory_id=(
            "pm_0123456789abcdef0123456789abcdef"
        ),
        user_id="user-001",
        category=PreferenceCandidateCategory.STYLE,
        value="休闲",
        direction=PreferenceDirection.PREFER,
        source=(
            PreferenceMemorySource.OUTFIT_FEEDBACK_CONFIRMATION
        ),
        source_reference_ids=("outfit-001",),
        confirmed_at=confirmed_at,
        last_confirmed_at=confirmed_at,
    )


@pytest.mark.anyio
async def test_postgres_repository_saves_memory() -> None:
    """验证仓库合并模型、刷新但不提交事务。"""

    session = AsyncMock(spec=AsyncSession)
    repository = PostgresPreferenceMemoryRepository(
        session,
    )
    memory = _memory()

    saved = await repository.save(memory)

    merged_model = session.merge.await_args.args[0]
    assert isinstance(
        merged_model,
        PreferenceMemoryModel,
    )
    assert merged_model.normalized_value == "休闲"
    session.flush.assert_awaited_once()
    session.commit.assert_not_awaited()
    assert saved is memory


@pytest.mark.anyio
async def test_postgres_repository_gets_by_identity() -> None:
    """验证查询使用用户、类别和规范化值。"""

    session = AsyncMock(spec=AsyncSession)
    result = Mock()
    result.scalar_one_or_none.return_value = (
        preference_memory_entity_to_model(_memory())
    )
    session.execute.return_value = result
    repository = PostgresPreferenceMemoryRepository(
        session,
    )

    found = await repository.get_by_identity(
        "user-001",
        PreferenceCandidateCategory.STYLE,
        " 休闲 ",
    )

    statement = session.execute.await_args.args[0]
    parameters = set(
        statement.compile().params.values(),
    )
    assert {
        "user-001",
        "style",
        "休闲",
    }.issubset(parameters)
    assert found == _memory()


@pytest.mark.anyio
async def test_postgres_repository_lists_and_deletes() -> None:
    """验证列表与批量删除复用当前请求事务。"""

    session = AsyncMock(spec=AsyncSession)
    model = preference_memory_entity_to_model(
        _memory(),
    )
    list_result = Mock()
    list_scalars = Mock()
    list_scalars.all.return_value = [model]
    list_result.scalars.return_value = list_scalars
    delete_result = Mock()
    delete_scalars = Mock()
    delete_scalars.all.return_value = [model]
    delete_result.scalars.return_value = delete_scalars
    session.execute.side_effect = [
        list_result,
        delete_result,
    ]
    repository = PostgresPreferenceMemoryRepository(
        session,
    )

    assert await repository.list_by_user_id(
        "user-001",
    ) == (_memory(),)
    assert await repository.delete_by_user_id(
        "user-001",
    ) == 1

    session.delete.assert_awaited_once_with(model)
    session.flush.assert_awaited_once()


@pytest.mark.anyio
async def test_postgres_repository_gets_and_deletes_by_id() -> None:
    """验证单条查询和删除同时使用用户 ID 限定范围。"""

    session = AsyncMock(spec=AsyncSession)
    model = preference_memory_entity_to_model(_memory())
    get_result = Mock()
    get_result.scalar_one_or_none.return_value = model
    delete_result = Mock()
    delete_result.scalar_one_or_none.return_value = model
    session.execute.side_effect = [
        get_result,
        delete_result,
    ]
    repository = PostgresPreferenceMemoryRepository(
        session,
    )

    found = await repository.get_by_id(
        "user-001",
        model.preference_memory_id,
    )
    deleted = await repository.delete_by_id(
        "user-001",
        model.preference_memory_id,
    )

    first_statement = session.execute.await_args_list[0].args[0]
    first_parameters = set(
        first_statement.compile().params.values(),
    )
    assert {
        "user-001",
        model.preference_memory_id,
    }.issubset(first_parameters)
    assert found == _memory()
    assert deleted is True
    session.delete.assert_awaited_once_with(model)
    session.flush.assert_awaited_once()
