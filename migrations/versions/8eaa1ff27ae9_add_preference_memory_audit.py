"""add preference memory audit

Revision ID: 8eaa1ff27ae9
Revises: a12f8c6d4e90
Create Date: 2026-08-02 19:57:50.712032

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# Alembic 使用这些标识确定迁移执行顺序
revision: str = "8eaa1ff27ae9"
down_revision: str | Sequence[str] | None = (
    "a12f8c6d4e90"
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """增加已确认长期偏好的来源和时间审计表。"""

    op.create_table(
        "preference_memories",
        sa.Column(
            "preference_memory_id",
            sa.String(length=35),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "category",
            sa.String(length=30),
            nullable=False,
        ),
        sa.Column(
            "value",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "normalized_value",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "direction",
            sa.String(length=10),
            nullable=False,
        ),
        sa.Column(
            "source",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "source_reference_ids",
            sa.JSON(),
            nullable=False,
        ),
        sa.Column(
            "confirmed_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "last_confirmed_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
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
            "category = 'style'",
            name="ck_preference_memories_category",
        ),
        sa.CheckConstraint(
            "direction IN ('prefer', 'avoid')",
            name="ck_preference_memories_direction",
        ),
        sa.CheckConstraint(
            "source = 'outfit_feedback_confirmation'",
            name="ck_preference_memories_source",
        ),
        sa.CheckConstraint(
            "length(normalized_value) > 0",
            name="ck_preference_memories_value_nonempty",
        ),
        sa.CheckConstraint(
            "last_confirmed_at >= confirmed_at",
            name=(
                "ck_preference_memories_confirmation_order"
            ),
        ),
        sa.CheckConstraint(
            (
                "expires_at IS NULL OR "
                "expires_at > last_confirmed_at"
            ),
            name="ck_preference_memories_expiry_order",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["style_profiles.user_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "preference_memory_id",
        ),
        sa.UniqueConstraint(
            "user_id",
            "category",
            "normalized_value",
            name="uq_preference_memories_identity",
        ),
    )
    op.create_index(
        "ix_preference_memories_user_category",
        "preference_memories",
        ["user_id", "category"],
        unique=False,
    )


def downgrade() -> None:
    """移除长期偏好审计表。"""

    op.drop_index(
        "ix_preference_memories_user_category",
        table_name="preference_memories",
    )
    op.drop_table("preference_memories")
