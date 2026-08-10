"""add wardrobe image assets

Revision ID: c2f7a9d4e1b0
Revises: 8eaa1ff27ae9
Create Date: 2026-08-10

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c2f7a9d4e1b0"
down_revision: str | Sequence[str] | None = "8eaa1ff27ae9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """创建图片资产元数据表，并给衣橱单品增加资产引用。"""

    op.create_table(
        "wardrobe_image_assets",
        sa.Column("user_id", sa.String(length=100), nullable=False),
        sa.Column("image_asset_id", sa.String(length=100), nullable=False),
        sa.Column("object_key", sa.String(length=500), nullable=False),
        sa.Column("content_type", sa.String(length=50), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attached_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending', 'uploaded', 'attached', 'deletion_pending', 'deleted')",
            name="ck_wardrobe_image_assets_status",
        ),
        sa.PrimaryKeyConstraint("user_id", "image_asset_id"),
        sa.UniqueConstraint("object_key"),
    )
    op.create_index(
        "ix_wardrobe_image_assets_user_status",
        "wardrobe_image_assets",
        ["user_id", "status"],
    )
    op.add_column(
        "wardrobe_items",
        sa.Column("image_asset_id", sa.String(length=100), nullable=True),
    )


def downgrade() -> None:
    """移除图片资产表和衣橱资产引用。"""

    op.drop_column("wardrobe_items", "image_asset_id")
    op.drop_index(
        "ix_wardrobe_image_assets_user_status",
        table_name="wardrobe_image_assets",
    )
    op.drop_table("wardrobe_image_assets")
