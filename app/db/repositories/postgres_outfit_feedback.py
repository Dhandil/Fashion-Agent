"""PostgreSQL Outfit 用户反馈仓库实现。"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.mappers.outfit_feedback import (
    outfit_feedback_entity_to_model,
    outfit_feedback_model_to_entity,
)
from app.db.models.outfit_feedback import (
    OutfitFeedbackModel,
)
from app.domain.entities.outfit_feedback import (
    OutfitFeedback,
    OutfitFeedbackSentiment,
)


class PostgresOutfitFeedbackRepository:
    """使用 SQLAlchemy AsyncSession 持久化 Outfit 反馈。"""

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """保存当前业务操作使用的数据库 Session。"""

        self._session = session

    async def get_by_outfit_id(
        self,
        user_id: str,
        outfit_id: str,
    ) -> OutfitFeedback | None:
        """读取当前用户对指定 Outfit 的反馈。"""

        statement = select(
            OutfitFeedbackModel,
        ).where(
            OutfitFeedbackModel.user_id == user_id,
            OutfitFeedbackModel.outfit_id == outfit_id,
        )

        result = await self._session.execute(statement)
        feedback_model = result.scalar_one_or_none()

        if feedback_model is None:
            return None

        return outfit_feedback_model_to_entity(
            feedback_model,
        )

    async def search(
        self,
        user_id: str,
        sentiment: OutfitFeedbackSentiment | None = None,
        limit: int = 20,
    ) -> list[OutfitFeedback]:
        """查询当前用户已经确认的 Outfit 反馈。"""

        statement = select(
            OutfitFeedbackModel,
        ).where(
            OutfitFeedbackModel.user_id == user_id,
        )

        if sentiment is not None:
            statement = statement.where(
                OutfitFeedbackModel.sentiment
                == sentiment.value,
            )

        statement = statement.order_by(
            OutfitFeedbackModel.updated_at.desc(),
            OutfitFeedbackModel.outfit_id.asc(),
        ).limit(limit)

        result = await self._session.execute(statement)
        feedback_models = result.scalars().all()

        return [
            outfit_feedback_model_to_entity(model)
            for model in feedback_models
        ]

    async def save(
        self,
        feedback: OutfitFeedback,
    ) -> OutfitFeedback:
        """新增或更新一套 Outfit 的当前反馈。"""

        feedback_model = (
            outfit_feedback_entity_to_model(
                feedback,
            )
        )

        await self._session.merge(feedback_model)
        await self._session.flush()

        return feedback

    async def delete(
        self,
        user_id: str,
        outfit_id: str,
    ) -> bool:
        """删除当前用户对指定 Outfit 的反馈。"""

        statement = select(
            OutfitFeedbackModel,
        ).where(
            OutfitFeedbackModel.user_id == user_id,
            OutfitFeedbackModel.outfit_id == outfit_id,
        )

        result = await self._session.execute(statement)
        feedback_model = result.scalar_one_or_none()

        if feedback_model is None:
            return False

        await self._session.delete(feedback_model)
        await self._session.flush()

        return True
