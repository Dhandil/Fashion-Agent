"""穿搭方案数据库模型。"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.db.models.base import Base


class OutfitModel(Base):
    """穿搭方案主表的 SQLAlchemy 映射。"""

    __tablename__ = "outfits"

    __table_args__ = (
        Index(
            "ix_outfits_user_scenario",
            "user_id",
            "scenario",
        ),
        Index(
            "ix_outfits_user_favorite",
            "user_id",
            "is_favorite",
        ),
    )

    # 用户 ID 和穿搭 ID 组成复合主键
    user_id: Mapped[str] = mapped_column(
        String(100),
        primary_key=True,
    )

    outfit_id: Mapped[str] = mapped_column(
        String(100),
        primary_key=True,
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    scenario: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    style_tags: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    season: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    recommendation_reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    is_favorite: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
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

    # 一套穿搭包含多个有顺序的单品
    items: Mapped[list["OutfitItemModel"]] = relationship(
        back_populates="outfit",
        cascade="all, delete-orphan",
        order_by="OutfitItemModel.position",
        lazy="selectin",
    )


class OutfitItemModel(Base):
    """穿搭方案中单个组成单品的数据库映射。"""

    __tablename__ = "outfit_items"

    __table_args__ = (
        # 单品必须属于一套真实存在的穿搭
        ForeignKeyConstraint(
            [
                "user_id",
                "outfit_id",
            ],
            [
                "outfits.user_id",
                "outfits.outfit_id",
            ],
            name="fk_outfit_items_outfit",
            ondelete="CASCADE",
        ),
        # 数据库层限制允许的单品来源
        CheckConstraint(
            (
                "source IN "
                "('wardrobe', 'product', 'recommendation')"
            ),
            name="ck_outfit_items_source",
        ),
        # 衣橱或商品来源必须能够追溯具体 ID
        CheckConstraint(
            (
                "source = 'recommendation' "
                "OR source_reference_id IS NOT NULL"
            ),
            name="ck_outfit_items_source_reference",
        ),
    )

    # 复制父表复合主键，用于用户隔离和外键关联
    user_id: Mapped[str] = mapped_column(
        String(100),
        primary_key=True,
    )

    outfit_id: Mapped[str] = mapped_column(
        String(100),
        primary_key=True,
    )

    # 单品在整套穿搭中的显示顺序
    position: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    role: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    source: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    source_reference_id: Mapped[
        str | None
    ] = mapped_column(
        String(100),
        nullable=True,
    )

    reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # 反向关联所属穿搭
    outfit: Mapped[OutfitModel] = relationship(
        back_populates="items",
    )