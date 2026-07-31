"""Outfit 用户反馈应用服务。"""

from dataclasses import dataclass

from app.core.exceptions import (
    OutfitFeedbackNotFoundError,
)
from app.domain.entities.outfit import Outfit
from app.domain.entities.outfit_feedback import (
    OutfitFeedback,
    OutfitFeedbackSentiment,
)
from app.domain.repositories.outfit import OutfitRepository
from app.domain.repositories.outfit_feedback import (
    OutfitFeedbackRepository,
)
from app.services.outfit import get_saved_outfit


@dataclass(
    frozen=True,
    slots=True,
)
class OutfitFeedbackSummary:
    """一条反馈及其关联 Outfit 的展示摘要。"""

    feedback: OutfitFeedback
    outfit: Outfit


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


async def list_recent_outfit_feedback(
    outfit_repository: OutfitRepository,
    feedback_repository: OutfitFeedbackRepository,
    user_id: str,
    sentiment: OutfitFeedbackSentiment | None = None,
    limit: int = 20,
) -> tuple[OutfitFeedbackSummary, ...]:
    """查询最近反馈，并批量关联对应的已保存 Outfit。"""

    feedback_items = await feedback_repository.search(
        user_id=user_id,
        sentiment=sentiment,
        limit=limit,
    )

    if not feedback_items:
        return ()

    outfit_ids = tuple(
        feedback.outfit_id
        for feedback in feedback_items
    )
    outfits = await outfit_repository.get_by_ids(
        user_id=user_id,
        outfit_ids=outfit_ids,
    )
    outfits_by_id = {
        outfit.outfit_id: outfit
        for outfit in outfits
    }

    # 按反馈仓库返回的最近更新时间顺序组织结果
    return tuple(
        OutfitFeedbackSummary(
            feedback=feedback,
            outfit=outfit,
        )
        for feedback in feedback_items
        if (
            outfit := outfits_by_id.get(
                feedback.outfit_id,
            )
        )
        is not None
    )


async def delete_saved_outfit_feedback(
    outfit_repository: OutfitRepository,
    feedback_repository: OutfitFeedbackRepository,
    user_id: str,
    outfit_id: str,
) -> None:
    """删除当前用户对指定 Outfit 的反馈。"""

    # 先验证 Outfit 归属，避免通过反馈接口探测其他用户的数据
    await get_saved_outfit(
        repository=outfit_repository,
        user_id=user_id,
        outfit_id=outfit_id,
    )

    deleted = await feedback_repository.delete(
        user_id=user_id,
        outfit_id=outfit_id,
    )

    if not deleted:
        raise OutfitFeedbackNotFoundError(
            "当前穿搭方案还没有用户反馈",
        )
