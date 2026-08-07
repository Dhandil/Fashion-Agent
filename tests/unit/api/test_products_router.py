"""商品目录 API 路由测试。"""

from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from app.api.routers.products import search_product_catalog
from app.domain.entities.product import Product


def _make_product(
    *,
    product_id: str = "p-001",
    name: str = "亚麻通勤衬衫",
    category: str = "衬衫",
    price: str = "299.00",
    in_stock: bool = True,
) -> Product:
    return Product(
        product_id=product_id,
        name=name,
        category=category,
        price=Decimal(price),
        in_stock=in_stock,
    )


@pytest.mark.anyio
async def test_search_product_catalog_returns_mapped_items() -> None:
    """验证搜索结果被正确映射为 API 响应（价格字符串化）。"""

    repository = AsyncMock()
    repository.search.return_value = [
        _make_product(),
    ]

    response = await search_product_catalog(
        product_repository=repository,
        query="衬衫",
    )

    assert response.count == 1
    assert response.total == 1
    assert response.items[0].name == "亚麻通勤衬衫"
    # 价格以字符串返回，避免浮点误差
    assert response.items[0].price == "299.00"
    assert response.items[0].currency == "CNY"


@pytest.mark.anyio
async def test_search_product_catalog_passes_filters() -> None:
    """验证关键词、品类、预算与数量限制原样传给仓库。"""

    repository = AsyncMock()
    repository.search.return_value = []

    await search_product_catalog(
        product_repository=repository,
        query="  衬衫  ",
        category="外套",
        max_price=Decimal("500.00"),
        limit=3,
    )

    repository.search.assert_awaited_once_with(
        query="衬衫",
        category="外套",
        max_price=Decimal("500.00"),
        limit=3,
    )


@pytest.mark.anyio
async def test_search_product_catalog_empty_query() -> None:
    """验证空关键词也能调用（返回目录前 N 件）。"""

    repository = AsyncMock()
    repository.search.return_value = []

    response = await search_product_catalog(
        product_repository=repository,
        query=None,
    )

    assert response.count == 0
    repository.search.assert_awaited_once_with(
        query="",
        category=None,
        max_price=None,
        limit=5,
    )
