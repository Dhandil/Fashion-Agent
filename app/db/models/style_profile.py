"""用户穿搭档案数据库模型。"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    JSON,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base


class StyleProfileModel(Base):
    """用户穿搭档案的 SQLAlchemy 数据库映射。"""

    __tablename__ = "style_profiles"

    # 数据库层再次保证最低预算不能高于最高预算
    __table_args__ = (
        CheckConstraint(
            (
                "typical_budget_min IS NULL "
                "OR typical_budget_max IS NULL "
                "OR typical_budget_min "
                "<= typical_budget_max"
            ),
            name="ck_style_profiles_budget_range",
        ),
    )

    # 当前使用外部身份系统提供的用户 ID
    # 认证系统完成前暂时不添加用户表外键
    user_id: Mapped[str] = mapped_column(
        String(100),
        primary_key=True,
    )

    preferred_styles: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    preferred_colors: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    avoided_colors: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    preferred_fits: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    avoided_materials: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    common_scenarios: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    typical_budget_min: Mapped[
        Decimal | None
    ] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    typical_budget_max: Mapped[
        Decimal | None
    ] = mapped_column(
        Numeric(12, 2),
        nullable=True,
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