"""Outfit 用户反馈仓库接口。"""

from typing import Protocol

from app.domain.entities.outfit_feedback import (
    OutfitFeedback,
    OutfitFeedbackSentiment,
)


class OutfitFeedbackRepository(Protocol):
    """定义 Outfit 反馈的持久化和查询能力。"""

    async def get_by_outfit_id(
        self,
        user_id: str,
        outfit_id: str,
    ) -> OutfitFeedback | None:
        """读取当前用户对指定 Outfit 的反馈。"""

        ...

    async def search(
        self,
        user_id: str,
        sentiment: OutfitFeedbackSentiment | None = None,
        limit: int = 20,
    ) -> list[OutfitFeedback]:
        """查询当前用户已经确认的 Outfit 反馈。"""

        ...

    async def save(
        self,
        feedback: OutfitFeedback,
    ) -> OutfitFeedback:
        """新增或更新一套 Outfit 的当前反馈。"""

        ...

    async def delete(
        self,
        user_id: str,
        outfit_id: str,
    ) -> bool:
        """删除当前用户对指定 Outfit 的反馈。"""

        ...
