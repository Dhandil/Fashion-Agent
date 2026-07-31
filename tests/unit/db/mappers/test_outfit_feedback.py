"""Outfit 反馈数据库 Mapper 测试。"""

from app.db.mappers.outfit_feedback import (
    outfit_feedback_entity_to_model,
    outfit_feedback_model_to_entity,
)
from app.domain.entities.outfit_feedback import (
    OutfitFeedback,
)


def test_outfit_feedback_mapper_preserves_data() -> None:
    """验证反馈经过双向转换后保持一致。"""

    feedback = OutfitFeedback(
        user_id="user-001",
        outfit_id="outfit-001",
        sentiment="dislike",
        comment="正式程度太高",
    )

    feedback_model = outfit_feedback_entity_to_model(
        feedback,
    )

    assert feedback_model.user_id == "user-001"
    assert feedback_model.outfit_id == "outfit-001"
    assert feedback_model.sentiment == "dislike"
    assert feedback_model.comment == "正式程度太高"

    restored_feedback = (
        outfit_feedback_model_to_entity(
            feedback_model,
        )
    )

    assert restored_feedback == feedback
