"""PostgreSQL 商品仓库测试。"""

from decimal import Decimal
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.product import ProductModel
from app.db.repositories.postgres_product import (
    PostgresProductRepository,
)


@pytest.mark.anyio
async def test_postgres_repository_searches_and_maps_products() -> None:
    """验证 PostgreSQL 仓库执行查询并转换商品实体。"""

    # 创建假的异步数据库 Session
    session = AsyncMock(spec=AsyncSession)

    # 模拟数据库查询得到的商品记录
    product_model = ProductModel(
        product_id="shirt-001",
        name="亚麻通勤衬衫",
        category="衬衫",
        price=Decimal("299.00"),
        currency="CNY",
        colors=["白色", "浅蓝色"],
        sizes=["S", "M", "L"],
        in_stock=True,
    )

    # 模拟 SQLAlchemy Result.scalars().all() 调用链
    scalar_result = Mock()
    scalar_result.all.return_value = [
        product_model,
    ]

    database_result = Mock()
    database_result.scalars.return_value = scalar_result

    # await session.execute(...) 后返回假查询结果
    session.execute.return_value = database_result

    # 创建使用假 Session 的 PostgreSQL 仓库
    repository = PostgresProductRepository(session)

    # 执行包含关键词、品类和预算的异步查询
    products = await repository.search(
        query="衬衫",
        category="衬衫",
        max_price=Decimal("350.00"),
        limit=5,
    )

    # 数据库查询应该只执行一次
    session.execute.assert_awaited_once()

    # 获取仓库构造的 SQLAlchemy 查询对象
    statement = session.execute.await_args.args[0]

    # 查询参数应该包含关键词、品类、预算和数量
    statement_parameters = statement.compile().params
    parameter_values = set(
        statement_parameters.values(),
    )

    assert "%衬衫%" in parameter_values
    assert "衬衫" in parameter_values
    assert Decimal("350.00") in parameter_values
    assert 5 in parameter_values

    # 数据库模型应该转换为领域实体
    assert len(products) == 1
    assert products[0].product_id == "shirt-001"
    assert products[0].price == Decimal("299.00")
    assert products[0].colors == (
        "白色",
        "浅蓝色",
    )