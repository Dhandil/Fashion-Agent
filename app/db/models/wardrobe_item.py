"""用户衣橱单品数据库模型。"""

from datetime import datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base


class WardrobeItemModel(Base):
    """用户衣橱单品的 SQLAlchemy 数据库映射。"""

    __tablename__ = "wardrobe_items"

    __table_args__ = (
        # 数据库层限制只能保存领域中定义的两种状态
        CheckConstraint(
            ("status IN ('available', 'unavailable')"),
            name="ck_wardrobe_items_status",
        ),
        # 常用查询是某个用户当前可以穿的衣物
        Index(
            "ix_wardrobe_items_user_status",
            "user_id",
            "status",
        ),
        # 支持查询用户衣橱中的指定品类
        Index(
            "ix_wardrobe_items_user_category",
            "user_id",
            "category",
        ),
    )

    # 用户 ID 放在复合主键第一位，方便按用户查询
    user_id: Mapped[str] = mapped_column(
        String(100),
        primary_key=True,
    )

    # 同一个单品 ID 可以在不同用户下独立存在
    wardrobe_item_id: Mapped[str] = mapped_column(
        String(100),
        primary_key=True,
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    category: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    brand: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    colors: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    materials: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    size: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    style_tags: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    seasons: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    scenarios: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    image_url: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    image_asset_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # 保存枚举的字符串值：available 或 unavailable
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="available",
    )

    notes: Mapped[str | None] = mapped_column(
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
