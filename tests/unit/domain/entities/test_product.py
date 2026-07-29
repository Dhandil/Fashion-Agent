from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.domain.entities.product import Product


def test_product_parses_price_and_collections() -> None:
    """验证商品价格和集合字段能够正确转换。"""

    product = Product(
        product_id="shirt-001",
        name="亚麻通勤衬衫",
        category="衬衫",
        price="299.00",
        colors=["白色", "浅蓝色"],
        sizes=["S", "M", "L"],
    )

    # 字符串价格应转换成精确的 Decimal
    assert product.price == Decimal("299.00")

    # 列表输入应转换成不可变元组
    assert product.colors == ("白色", "浅蓝色")
    assert product.sizes == ("S", "M", "L")

    # 未传入的库存字段使用默认值
    assert product.in_stock is True


def test_product_rejects_negative_price() -> None:
    """验证商品价格不能为负数。"""

    with pytest.raises(ValidationError):
        Product(
            product_id="shirt-002",
            name="测试衬衫",
            category="衬衫",
            price="-1.00",
        )


def test_product_is_immutable() -> None:
    """验证商品创建后不能直接修改。"""

    product = Product(
        product_id="shirt-003",
        name="纯棉衬衫",
        category="衬衫",
        price="199.00",
    )

    with pytest.raises(ValidationError):
        product.price = Decimal("99.00")