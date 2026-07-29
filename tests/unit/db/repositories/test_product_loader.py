from decimal import Decimal
from pathlib import Path

from app.db.repositories.product_loader import (
    load_products_from_json,
)


def test_load_products_from_json(
    tmp_path: Path,
) -> None:
    """验证 JSON 商品文件可以转换成 Product 列表。"""

    # 在 pytest 临时目录中创建商品文件
    product_file = tmp_path / "products.json"
    product_file.write_text(
        """
        [
          {
            "product_id": "shirt-001",
            "name": "亚麻通勤衬衫",
            "category": "衬衫",
            "price": "299.00",
            "colors": ["白色", "浅蓝色"],
            "sizes": ["S", "M", "L"],
            "in_stock": true
          }
        ]
        """,
        encoding="utf-8",
    )

    # 加载并校验商品
    products = load_products_from_json(product_file)

    assert len(products) == 1

    product = products[0]

    # 验证基础字段
    assert product.product_id == "shirt-001"
    assert product.name == "亚麻通勤衬衫"

    # 验证字符串价格转换成 Decimal
    assert product.price == Decimal("299.00")

    # 验证列表转换成不可变元组
    assert product.colors == ("白色", "浅蓝色")
    assert product.sizes == ("S", "M", "L")

    # 验证未提供的货币字段使用默认值
    assert product.currency == "CNY"