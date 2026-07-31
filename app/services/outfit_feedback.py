"""Outfit 用户反馈应用服务。"""

from app.core.exceptions import (
    OutfitFeedbackNotFoundError,
)
from app.domain.entities.outfit_feedback import (
    OutfitFeedback,
    OutfitFeedbackSentiment,
)
from app.domain.repositories.outfit import OutfitRepository
from app.domain.repositories.outfit_feedback import (
    OutfitFeedbackRepository,
)
from app.services.outfit import get_saved_outfit


async def save_outfit_feedback(
    outfit_repository: OutfitRepository,
    feedback_repository: OutfitFeedbackRepository,
    user_id: str,
    outfit_id: str,
    sentiment: OutfitFeedbackSentiment | None = None,
    comment: str | None = None,
) -> OutfitFeedback:
    """保存当前用户对指定 Outfit 的最新反馈。"""

    # 先校验 Outfit 所有权，避免为其他用户或不存在的 Outfit 写入反馈
    await get_saved_outfit(
        repository=outfit_repository,
        user_id=user_id,
        outfit_id=outfit_id,
    )

    feedback = OutfitFeedback(
        user_id=user_id,
        outfit_id=outfit_id,
        sentiment=sentiment,
        comment=comment,
    )

    return await feedback_repository.save(
        feedback,
    )


async def get_saved_outfit_feedback(
    outfit_repository: OutfitRepository,
    feedback_repository: OutfitFeedbackRepository,
    user_id: str,
    outfit_id: str,
) -> OutfitFeedback:
    """读取当前用户对指定 Outfit 的已有反馈。"""

    # 分开校验 Outfit 和反馈，向调用方返回准确且不泄露其他用户数据的错误
    await get_saved_outfit(
        repository=outfit_repository,
        user_id=user_id,
        outfit_id=outfit_id,
    )

    feedback = await feedback_repository.get_by_outfit_id(
        user_id=user_id,
        outfit_id=outfit_id,
    )

    if feedback is None:
        raise OutfitFeedbackNotFoundError(
            "当前穿搭方案还没有用户反馈",
        )

    return feedback
