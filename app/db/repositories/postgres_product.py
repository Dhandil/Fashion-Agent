"""PostgreSQL 商品仓库实现。"""

from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.mappers.product import (
    product_model_to_entity,
)
from app.db.models.product import ProductModel
from app.domain.entities.product import Product


class PostgresProductRepository:
    """使用 SQLAlchemy AsyncSession 查询 PostgreSQL 商品。"""

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """保存当前业务操作使用的数据库 Session。"""

        self._session = session

    async def search(
        self,
        query: str,
        category: str | None = None,
        max_price: Decimal | None = None,
        limit: int = 5,
    ) -> list[Product]:
        """根据关键词和过滤条件异步搜索有库存商品。"""

        # 去除搜索关键词首尾空格
        normalized_query = query.strip()

        # 从商品表构建查询，并默认只返回有库存商品
        statement = select(ProductModel).where(
            ProductModel.in_stock.is_(True),
        )

        # 关键词不为空时，在商品名称和品类中执行模糊查询
        if normalized_query:
            search_pattern = f"%{normalized_query}%"

            statement = statement.where(
                or_(
                    ProductModel.name.ilike(
                        search_pattern,
                    ),
                    ProductModel.category.ilike(
                        search_pattern,
                    ),
                ),
            )

        # 用户提供品类时增加精确品类过滤
        if category is not None:
            statement = statement.where(
                ProductModel.category == category,
            )

        # 用户提供预算时过滤超过最高价格的商品
        if max_price is not None:
            statement = statement.where(
                ProductModel.price <= max_price,
            )

        # 先按价格排序，再限制返回数量
        statement = statement.order_by(
            ProductModel.price.asc(),
            ProductModel.product_id.asc(),
        ).limit(limit)

        # 异步执行 SQL 查询
        result = await self._session.execute(statement)

        # scalars() 只取得 ProductModel，不返回 SQL 行包装对象
        product_models = result.scalars().all()

        # 数据库模型不能直接进入领域层，需要逐个转换
        return [
            product_model_to_entity(product_model)
            for product_model in product_models
        ]