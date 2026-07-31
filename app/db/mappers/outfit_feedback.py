"""Outfit 反馈领域实体与数据库模型转换。"""

from app.db.models.outfit_feedback import (
    OutfitFeedbackModel,
)
from app.domain.entities.outfit_feedback import (
    OutfitFeedback,
    OutfitFeedbackSentiment,
)


def outfit_feedback_entity_to_model(
    feedback: OutfitFeedback,
) -> OutfitFeedbackModel:
    """把 Outfit 反馈领域实体转换成数据库模型。"""

    return OutfitFeedbackModel(
        user_id=feedback.user_id,
        outfit_id=feedback.outfit_id,
        sentiment=(
            feedback.sentiment.value
            if feedback.sentiment is not None
            else None
        ),
        comment=feedback.comment,
    )


def outfit_feedback_model_to_entity(
    model: OutfitFeedbackModel,
) -> OutfitFeedback:
    """把 Outfit 反馈数据库模型转换成领域实体。"""

    return OutfitFeedback(
        user_id=model.user_id,
        outfit_id=model.outfit_id,
        sentiment=(
            OutfitFeedbackSentiment(model.sentiment)
            if model.sentiment is not None
            else None
        ),
        comment=model.comment,
    )
