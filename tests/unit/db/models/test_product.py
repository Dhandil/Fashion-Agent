"""商品数据库模型测试。"""

from sqlalchemy import Numeric

from app.db.models.product import ProductModel


def test_product_model_defines_required_columns() -> None:
    """验证商品表包含当前领域模型需要的字段。"""

    # __table__ 是 SQLAlchemy 根据模型生成的表元数据
    product_table = ProductModel.__table__

    # 验证真实数据库表名
    assert product_table.name == "products"

    # 获取表中所有列名
    column_names = set(product_table.columns.keys())

    # 当前商品持久化需要的全部字段
    required_columns = {
        "product_id",
        "name",
        "category",
        "price",
        "currency",
        "colors",
        "sizes",
        "in_stock",
        "created_at",
        "updated_at",
    }

    assert required_columns == column_names


def test_product_model_defines_primary_key_and_price_type() -> None:
    """验证商品主键和价格精度配置。"""

    product_table = ProductModel.__table__

    # 商品 ID 应该是表的唯一主键
    primary_key_columns = list(
        product_table.primary_key.columns.keys(),
    )
    assert primary_key_columns == ["product_id"]

    # 获取价格列的 SQLAlchemy 类型
    price_type = product_table.columns["price"].type

    # 价格必须使用 Numeric，而不是存在精度误差的 Float
    assert isinstance(price_type, Numeric)
    assert price_type.precision == 12
    assert price_type.scale == 2