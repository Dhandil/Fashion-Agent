"""Outfit 用户反馈数据库模型。"""

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base


class OutfitFeedbackModel(Base):
    """用户对一套已保存 Outfit 的当前反馈。"""

    __tablename__ = "outfit_feedback"

    __table_args__ = (
        ForeignKeyConstraint(
            [
                "user_id",
                "outfit_id",
            ],
            [
                "outfits.user_id",
                "outfits.outfit_id",
            ],
            name="fk_outfit_feedback_outfit",
            ondelete="CASCADE",
        ),
        CheckConstraint(
            (
                "sentiment IS NULL "
                "OR sentiment IN ('like', 'dislike')"
            ),
            name="ck_outfit_feedback_sentiment",
        ),
        CheckConstraint(
            (
                "sentiment IS NOT NULL "
                "OR comment IS NOT NULL"
            ),
            name="ck_outfit_feedback_content",
        ),
        Index(
            "ix_outfit_feedback_user_sentiment",
            "user_id",
            "sentiment",
        ),
    )

    # 与 Outfit 使用相同复合键，同时保证每套穿搭只有一份当前反馈
    user_id: Mapped[str] = mapped_column(
        String(100),
        primary_key=True,
    )

    outfit_id: Mapped[str] = mapped_column(
        String(100),
        primary_key=True,
    )

    sentiment: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    comment: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
