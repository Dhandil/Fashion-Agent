"""add outfit feedback

Revision ID: e955247b6080
Revises: b81f4a2d9c30
Create Date: 2026-07-31 10:50:38.920856

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# Alembic 使用这些标识确定迁移执行顺序
revision: str = "e955247b6080"
down_revision: str | Sequence[str] | None = (
    "b81f4a2d9c30"
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """创建 Outfit 用户当前反馈表。"""

    op.create_table(
        "outfit_feedback",
        sa.Column(
            "user_id",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "outfit_id",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "sentiment",
            sa.String(length=20),
            nullable=True,
        ),
        sa.Column(
            "comment",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            (
                "sentiment IS NULL "
                "OR sentiment IN ('like', 'dislike')"
            ),
            name="ck_outfit_feedback_sentiment",
        ),
        sa.CheckConstraint(
            (
                "sentiment IS NOT NULL "
                "OR comment IS NOT NULL"
            ),
            name="ck_outfit_feedback_content",
        ),
        sa.ForeignKeyConstraint(
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
        sa.PrimaryKeyConstraint(
            "user_id",
            "outfit_id",
        ),
    )
    op.create_index(
        "ix_outfit_feedback_user_sentiment",
        "outfit_feedback",
        [
            "user_id",
            "sentiment",
        ],
        unique=False,
    )


def downgrade() -> None:
    """删除 Outfit 用户当前反馈表。"""

    op.drop_index(
        "ix_outfit_feedback_user_sentiment",
        table_name="outfit_feedback",
    )
    op.drop_table(
        "outfit_feedback",
    )
