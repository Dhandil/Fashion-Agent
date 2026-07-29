from collections.abc import Iterable
from decimal import Decimal

from app.domain.entities.product import Product


class InMemoryProductRepository:
    """从内存商品集合中搜索商品。"""

    def __init__(
        self,
        prodcts: Iterable[Product],
    ) -> None:
        """保存一份不可变的商品集合。"""

        self._products = tuple(prodcts)

    def search(
        self,
        query: str,
        category: str | None = None,
        max_price: Decimal | None = None,
        limit: int = 5,
    ) -> list[Product]:
        """根据关键词和过滤条件搜索商品。"""

        # 统一关键词格式，减少大小写和首尾空格影响
        normalized_query = query.strip().lower()

        matched_products: list[Product] = []

        for product in self._products:
            # 关键词需要出现在商品名称或品类中
            searchable_text = (
                f"{product.name} {product.category}"
            ).lower()

            if normalized_query not in searchable_text:
                continue

            # 提供品类时执行精确品类过滤
            if (
                category is not None
                and product.category != category
            ):
                continue

            # 提供最高价格时过滤超出预算的商品
            if (
                max_price is not None
                and product.price > max_price
            ):
                continue

            # 当前只返回有库存商品
            if not product.in_stock:
                continue

            matched_products.append(product)

            # 达到返回数量限制后停止搜索
            if len(matched_products) >= limit:
                break

        return matched_products
            