"""Outfit 用户反馈应用服务测试。"""

from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import (
    OutfitFeedbackNotFoundError,
)
from app.domain.entities.outfit import Outfit, OutfitItem
from app.domain.entities.outfit_feedback import (
    OutfitFeedback,
    OutfitFeedbackSentiment,
)
from app.domain.repositories.outfit import OutfitRepository
from app.domain.repositories.outfit_feedback import (
    OutfitFeedbackRepository,
)
from app.services.outfit_feedback import (
    get_saved_outfit_feedback,
    save_outfit_feedback,
)


def create_saved_outfit() -> Outfit:
    """创建反馈服务测试使用的已保存穿搭。"""

    return Outfit(
        outfit_id="outfit-001",
        user_id="user-001",
        name="夏季通勤搭配",
        scenario="通勤",
        items=(
            OutfitItem(
                role="上装",
                name="浅蓝色亚麻衬衫",
                source="wardrobe",
                source_reference_id="shirt-001",
            ),
        ),
        recommendation_reason="优先使用已有衣物。",
    )


@pytest.mark.anyio
async def test_save_outfit_feedback_checks_ownership() -> None:
    """验证服务校验 Outfit 归属后再保存反馈。"""

    outfit_repository = AsyncMock(
        spec=OutfitRepository,
    )
    outfit_repository.get_by_id.return_value = (
        create_saved_outfit()
    )
    feedback_repository = AsyncMock(
        spec=OutfitFeedbackRepository,
    )
    feedback_repository.save.side_effect = (
        lambda feedback: feedback
    )

    feedback = await save_outfit_feedback(
        outfit_repository=outfit_repository,
        feedback_repository=feedback_repository,
        user_id="user-001",
        outfit_id="outfit-001",
        sentiment=OutfitFeedbackSentiment.LIKE,
        comment="  配色很适合我  ",
    )

    assert feedback.user_id == "user-001"
    assert feedback.outfit_id == "outfit-001"
    assert feedback.sentiment == (
        OutfitFeedbackSentiment.LIKE
    )
    assert feedback.comment == "配色很适合我"
    outfit_repository.get_by_id.assert_awaited_once_with(
        user_id="user-001",
        outfit_id="outfit-001",
    )
    feedback_repository.save.assert_awaited_once_with(
        feedback,
    )


@pytest.mark.anyio
async def test_get_saved_outfit_feedback_returns_feedback() -> None:
    """验证服务读取属于当前用户的 Outfit 反馈。"""

    outfit_repository = AsyncMock(
        spec=OutfitRepository,
    )
    outfit_repository.get_by_id.return_value = (
        create_saved_outfit()
    )
    expected_feedback = OutfitFeedback(
        user_id="user-001",
        outfit_id="outfit-001",
        sentiment=OutfitFeedbackSentiment.DISLIKE,
        comment="不喜欢上衣颜色",
    )
    feedback_repository = AsyncMock(
        spec=OutfitFeedbackRepository,
    )
    feedback_repository.get_by_outfit_id.return_value = (
        expected_feedback
    )

    feedback = await get_saved_outfit_feedback(
        outfit_repository=outfit_repository,
        feedback_repository=feedback_repository,
        user_id="user-001",
        outfit_id="outfit-001",
    )

    assert feedback is expected_feedback
    feedback_repository.get_by_outfit_id.assert_awaited_once_with(
        user_id="user-001",
        outfit_id="outfit-001",
    )


@pytest.mark.anyio
async def test_get_saved_outfit_feedback_requires_feedback() -> None:
    """验证 Outfit 存在但没有反馈时返回明确错误。"""

    outfit_repository = AsyncMock(
        spec=OutfitRepository,
    )
    outfit_repository.get_by_id.return_value = (
        create_saved_outfit()
    )
    feedback_repository = AsyncMock(
        spec=OutfitFeedbackRepository,
    )
    feedback_repository.get_by_outfit_id.return_value = None

    with pytest.raises(
        OutfitFeedbackNotFoundError,
        match="还没有用户反馈",
    ):
        await get_saved_outfit_feedback(
            outfit_repository=outfit_repository,
            feedback_repository=feedback_repository,
            user_id="user-001",
            outfit_id="outfit-001",
        )
