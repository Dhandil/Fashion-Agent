"""add avoided styles to style profiles

Revision ID: a12f8c6d4e90
Revises: e955247b6080
Create Date: 2026-07-31

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# Alembic 使用这些标识确定迁移执行顺序
revision: str = "a12f8c6d4e90"
down_revision: str | Sequence[str] | None = (
    "e955247b6080"
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """为长期档案增加希望避免的风格列表。"""

    op.add_column(
        "style_profiles",
        sa.Column(
            "avoided_styles",
            sa.JSON(),
            server_default=sa.text("'[]'::json"),
            nullable=False,
        ),
    )

    # 默认值只用于安全迁移已有数据，后续默认值由应用模型负责
    op.alter_column(
        "style_profiles",
        "avoided_styles",
        server_default=None,
    )


def downgrade() -> None:
    """移除长期档案的希望避免风格列表。"""

    op.drop_column(
        "style_profiles",
        "avoided_styles",
    )
