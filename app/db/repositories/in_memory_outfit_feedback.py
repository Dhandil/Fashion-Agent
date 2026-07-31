"""Outfit 用户反馈的内存仓库实现。"""

from collections.abc import Iterable

from app.domain.entities.outfit_feedback import (
    OutfitFeedback,
    OutfitFeedbackSentiment,
)


class InMemoryOutfitFeedbackRepository:
    """在当前 Python 进程中保存 Outfit 反馈。"""

    def __init__(
        self,
        feedback_items: Iterable[
            OutfitFeedback
        ] | None = None,
    ) -> None:
        """使用可选反馈初始化内存仓库。"""

        self._feedback = {
            (
                feedback.user_id,
                feedback.outfit_id,
            ): feedback
            for feedback in feedback_items or ()
        }

    async def get_by_outfit_id(
        self,
        user_id: str,
        outfit_id: str,
    ) -> OutfitFeedback | None:
        """读取当前用户对指定 Outfit 的反馈。"""

        return self._feedback.get(
            (
                user_id,
                outfit_id,
            ),
        )

    async def search(
        self,
        user_id: str,
        sentiment: OutfitFeedbackSentiment | None = None,
        limit: int = 20,
    ) -> list[OutfitFeedback]:
        """查询当前用户已经确认的 Outfit 反馈。"""

        matched_feedback: list[OutfitFeedback] = []

        for feedback in self._feedback.values():
            if feedback.user_id != user_id:
                continue

            if (
                sentiment is not None
                and feedback.sentiment is not sentiment
            ):
                continue

            matched_feedback.append(feedback)

            if len(matched_feedback) >= limit:
                break

        return matched_feedback

    async def save(
        self,
        feedback: OutfitFeedback,
    ) -> OutfitFeedback:
        """新增或替换一套 Outfit 的当前反馈。"""

        self._feedback[
            (
                feedback.user_id,
                feedback.outfit_id,
            )
        ] = feedback

        return feedback

    async def delete(
        self,
        user_id: str,
        outfit_id: str,
    ) -> bool:
        """删除当前用户对指定 Outfit 的反馈。"""

        deleted_feedback = self._feedback.pop(
            (
                user_id,
                outfit_id,
            ),
            None,
        )

        return deleted_feedback is not None
