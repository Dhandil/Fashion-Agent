"""simplify wardrobe item status

Revision ID: b81f4a2d9c30
Revises: da6349c5e3de
Create Date: 2026-07-30

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# Alembic 使用这些标识确定迁移执行顺序
revision: str = "b81f4a2d9c30"
down_revision: str | Sequence[str] | None = "da6349c5e3de"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """将衣物状态归一为可用或不可用。"""

    # 先移除旧约束，才能把 laundry 数据更新为 unavailable
    op.drop_constraint(
        "ck_wardrobe_items_status",
        "wardrobe_items",
        type_="check",
    )

    # 清洗中的衣物对搭配推荐而言同样属于暂不可用
    op.execute(
        sa.text(
            "UPDATE wardrobe_items SET status = 'unavailable' WHERE status = 'laundry'",
        ),
    )

    op.create_check_constraint(
        "ck_wardrobe_items_status",
        "wardrobe_items",
        "status IN ('available', 'unavailable')",
    )


def downgrade() -> None:
    """恢复允许旧的 laundry 状态。"""

    op.drop_constraint(
        "ck_wardrobe_items_status",
        "wardrobe_items",
        type_="check",
    )

    # 已归一为 unavailable 的历史数据无法自动判断原先是否为 laundry
    op.create_check_constraint(
        "ck_wardrobe_items_status",
        "wardrobe_items",
        "status IN ('available', 'laundry', 'unavailable')",
    )
