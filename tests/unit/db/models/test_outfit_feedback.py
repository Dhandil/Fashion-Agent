"""Outfit 反馈 SQLAlchemy 模型测试。"""

from app.db.models.outfit_feedback import (
    OutfitFeedbackModel,
)


def test_outfit_feedback_model_uses_composite_primary_key() -> None:
    """验证每个用户对每套 Outfit 只有一份当前反馈。"""

    primary_key_columns = {
        column.name
        for column in (
            OutfitFeedbackModel.__table__.primary_key.columns
        )
    }

    assert primary_key_columns == {
        "user_id",
        "outfit_id",
    }


def test_outfit_feedback_model_has_validation_constraints() -> None:
    """验证数据库层限制反馈态度和空内容。"""

    constraint_names = {
        constraint.name
        for constraint in (
            OutfitFeedbackModel.__table__.constraints
        )
    }

    assert "ck_outfit_feedback_sentiment" in (
        constraint_names
    )
    assert "ck_outfit_feedback_content" in (
        constraint_names
    )
    assert "fk_outfit_feedback_outfit" in (
        constraint_names
    )
