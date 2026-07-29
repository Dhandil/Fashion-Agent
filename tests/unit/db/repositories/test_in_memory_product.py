import pytest

from decimal import Decimal

from app.db.repositories.in_memory_product import (
    InMemoryProductRepository,
)
from app.domain.entities.product import Product


@pytest.mark.anyio
async def test_repository_filters_products() -> None:
    """验证商品搜索的关键词、预算和库存过滤。"""

    products = [
        Product(
            product_id="shirt-001",
            name="亚麻通勤衬衫",
            category="衬衫",
            price="299.00",
            in_stock=True,
        ),
        Product(
            product_id="shirt-002",
            name="纯棉休闲衬衫",
            category="衬衫",
            price="199.00",
            in_stock=False,
        ),
        Product(
            product_id="shirt-003",
            name="高端亚麻衬衫",
            category="衬衫",
            price="399.00",
            in_stock=True,
        ),
        Product(
            product_id="coat-001",
            name="羊毛通勤外套",
            category="外套",
            price="599.00",
            in_stock=True,
        ),
    ]

    repository = InMemoryProductRepository(products)

    results = await repository.search(
        query="衬衫",
        category="衬衫",
        max_price=Decimal("350.00"),
        limit=5,
    )

    # 只有第一件商品同时满足全部条件
    assert len(results) == 1
    assert results[0].product_id == "shirt-001"