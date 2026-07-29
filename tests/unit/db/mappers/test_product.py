"""商品数据库模型与领域实体转换测试。"""

from decimal import Decimal

from app.db.mappers.product import (
    product_entity_to_model,
    product_model_to_entity,
)
from app.domain.entities.product import Product


def test_product_mapper_preserves_product_data() -> None:
    """验证商品经过双向转换后业务数据保持一致。"""

    # 创建业务层使用的不可变商品实体
    product = Product(
        product_id="shirt-001",
        name="亚麻通勤衬衫",
        category="衬衫",
        price=Decimal("299.00"),
        currency="CNY",
        colors=("白色", "浅蓝色"),
        sizes=("S", "M", "L"),
        in_stock=True,
    )

    # 模拟商品写入数据库前的转换
    product_model = product_entity_to_model(product)

    # 数据库 JSON 字段应该使用可序列化的列表
    assert product_model.colors == ["白色", "浅蓝色"]
    assert product_model.sizes == ["S", "M", "L"]

    # 模拟从数据库读取后转换回领域实体
    restored_product = product_model_to_entity(
        product_model,
    )

    # 所有业务字段应该与转换前保持一致
    assert restored_product == product

    # 价格应该继续使用 Decimal
    assert restored_product.price == Decimal("299.00")

    # 领域实体中的颜色和尺码应该恢复为元组
    assert restored_product.colors == (
        "白色",
        "浅蓝色",
    )
    assert restored_product.sizes == (
        "S",
        "M",
        "L",
    )