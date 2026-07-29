from decimal import Decimal
from typing import Protocol

from app.domain.entities.product import Product


class ProductRepository(Protocol):
    """商品数据访问接口。"""

    async def search(
        self,
        query: str,
        category: str | None = None,
        max_price: Decimal | None = None,
        limit: int = 5,
    ) -> list[Product]:
        """根据关键词和过滤条件异步搜索商品。"""
