"""商品数据库模型。"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    JSON,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base


class ProductModel(Base):
    """商品表的 SQLAlchemy 数据库映射模型。"""

    # PostgreSQL 中实际使用的表名
    __tablename__ = "products"

    # 项目内部商品唯一标识
    product_id: Mapped[str] = mapped_column(
        String(100),
        primary_key=True,
    )

    # 商品展示名称，并为常用搜索字段创建索引
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    # 商品品类，例如衬衫、外套
    category: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    # 商品价格使用定点数，避免浮点数精度问题
    price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    # ISO 4217 货币代码，例如 CNY
    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="CNY",
    )

    # 商品可选颜色，以 JSON 数组保存
    colors: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    # 商品可选尺码，以 JSON 数组保存
    sizes: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    # 是否有库存，并为库存过滤创建索引
    in_stock: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    # 数据首次写入数据库的时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # 数据最后一次更新的时间
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )