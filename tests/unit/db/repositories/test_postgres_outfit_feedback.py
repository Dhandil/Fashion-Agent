"""PostgreSQL Outfit 反馈仓库测试。"""

from unittest.mock import (
    AsyncMock,
    Mock,
)

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.outfit_feedback import (
    OutfitFeedbackModel,
)
from app.db.repositories.postgres_outfit_feedback import (
    PostgresOutfitFeedbackRepository,
)
from app.domain.entities.outfit_feedback import (
    OutfitFeedback,
    OutfitFeedbackSentiment,
)


def create_feedback() -> OutfitFeedback:
    """创建多个仓库测试复用的反馈实体。"""

    return OutfitFeedback(
        user_id="user-001",
        outfit_id="outfit-001",
        sentiment="like",
        comment="配色很适合通勤",
    )


@pytest.mark.anyio
async def test_repository_saves_feedback() -> None:
    """验证仓库合并反馈并刷新 Session。"""

    session = AsyncMock(
        spec=AsyncSession,
    )
    repository = PostgresOutfitFeedbackRepository(
        session,
    )
    feedback = create_feedback()

    saved_feedback = await repository.save(
        feedback,
    )

    session.merge.assert_awaited_once()
    feedback_model = session.merge.await_args.args[0]
    assert isinstance(
        feedback_model,
        OutfitFeedbackModel,
    )
    assert feedback_model.sentiment == "like"
    session.flush.assert_awaited_once()
    session.commit.assert_not_awaited()
    assert saved_feedback is feedback


@pytest.mark.anyio
async def test_repository_gets_feedback_by_outfit() -> None:
    """验证查询同时使用用户和 Outfit ID。"""

    session = AsyncMock(
        spec=AsyncSession,
    )
    repository = PostgresOutfitFeedbackRepository(
        session,
    )
    feedback_model = OutfitFeedbackModel(
        user_id="user-001",
        outfit_id="outfit-001",
        sentiment="like",
        comment=None,
    )
    database_result = Mock()
    database_result.scalar_one_or_none.return_value = (
        feedback_model
    )
    session.execute.return_value = database_result

    feedback = await repository.get_by_outfit_id(
        user_id="user-001",
        outfit_id="outfit-001",
    )

    statement = session.execute.await_args.args[0]
    parameter_values = set(
        statement.compile().params.values(),
    )
    assert "user-001" in parameter_values
    assert "outfit-001" in parameter_values
    assert feedback is not None
    assert feedback.sentiment is (
        OutfitFeedbackSentiment.LIKE
    )


@pytest.mark.anyio
async def test_repository_searches_feedback() -> None:
    """验证仓库按用户和态度查询反馈。"""

    session = AsyncMock(
        spec=AsyncSession,
    )
    repository = PostgresOutfitFeedbackRepository(
        session,
    )
    feedback_model = OutfitFeedbackModel(
        user_id="user-001",
        outfit_id="outfit-001",
        sentiment="dislike",
        comment="不喜欢正式裤装",
    )
    scalar_result = Mock()
    scalar_result.all.return_value = [
        feedback_model,
    ]
    database_result = Mock()
    database_result.scalars.return_value = (
        scalar_result
    )
    session.execute.return_value = database_result

    feedback_items = await repository.search(
        user_id="user-001",
        sentiment=(
            OutfitFeedbackSentiment.DISLIKE
        ),
        limit=10,
    )

    statement = session.execute.await_args.args[0]
    parameter_values = set(
        statement.compile().params.values(),
    )
    assert "user-001" in parameter_values
    assert "dislike" in parameter_values
    assert 10 in parameter_values
    assert len(feedback_items) == 1


@pytest.mark.anyio
async def test_repository_deletes_existing_feedback() -> None:
    """验证仓库删除当前用户指定 Outfit 的反馈。"""

    session = AsyncMock(
        spec=AsyncSession,
    )
    repository = PostgresOutfitFeedbackRepository(
        session,
    )
    feedback_model = OutfitFeedbackModel(
        user_id="user-001",
        outfit_id="outfit-001",
        sentiment="like",
        comment=None,
    )
    database_result = Mock()
    database_result.scalar_one_or_none.return_value = (
        feedback_model
    )
    session.execute.return_value = database_result

    deleted = await repository.delete(
        user_id="user-001",
        outfit_id="outfit-001",
    )

    assert deleted is True
    session.delete.assert_awaited_once_with(
        feedback_model,
    )
    session.flush.assert_awaited_once()
