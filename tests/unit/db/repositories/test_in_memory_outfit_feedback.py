"""Outfit 反馈内存仓库测试。"""

import pytest

from app.db.repositories.in_memory_outfit_feedback import (
    InMemoryOutfitFeedbackRepository,
)
from app.domain.entities.outfit_feedback import (
    OutfitFeedback,
    OutfitFeedbackSentiment,
)


@pytest.mark.anyio
async def test_repository_isolates_users_and_filters_sentiment() -> None:
    """验证反馈查询按用户隔离并支持态度过滤。"""

    repository = InMemoryOutfitFeedbackRepository(
        feedback_items=[
            OutfitFeedback(
                user_id="user-001",
                outfit_id="outfit-001",
                sentiment="like",
            ),
            OutfitFeedback(
                user_id="user-001",
                outfit_id="outfit-002",
                sentiment="dislike",
            ),
            OutfitFeedback(
                user_id="user-002",
                outfit_id="outfit-003",
                sentiment="like",
            ),
        ],
    )

    liked_feedback = await repository.search(
        user_id="user-001",
        sentiment=OutfitFeedbackSentiment.LIKE,
    )

    assert len(liked_feedback) == 1
    assert liked_feedback[0].outfit_id == (
        "outfit-001"
    )


@pytest.mark.anyio
async def test_repository_updates_and_deletes_feedback() -> None:
    """验证同一 Outfit 的反馈会更新且可以删除。"""

    repository = InMemoryOutfitFeedbackRepository()
    original_feedback = OutfitFeedback(
        user_id="user-001",
        outfit_id="outfit-001",
        sentiment="like",
    )
    updated_feedback = OutfitFeedback(
        user_id="user-001",
        outfit_id="outfit-001",
        sentiment="dislike",
        comment="正式程度太高",
    )

    await repository.save(original_feedback)
    await repository.save(updated_feedback)

    assert (
        await repository.get_by_outfit_id(
            user_id="user-001",
            outfit_id="outfit-001",
        )
        == updated_feedback
    )

    assert (
        await repository.delete(
            user_id="user-001",
            outfit_id="outfit-001",
        )
        is True
    )
    assert (
        await repository.get_by_outfit_id(
            user_id="user-001",
            outfit_id="outfit-001",
        )
        is None
    )
