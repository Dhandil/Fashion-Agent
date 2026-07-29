import json, pytest
from decimal import Decimal
from unittest.mock import Mock

from app.domain.entities.product import Product
from app.domain.repositories.product import ProductRepository
from app.tools.builtins.product_search import (
    create_product_search_tool,
)


@pytest.mark.anyio
async def test_product_search_tool_returns_json_products() -> None:
    """验证商品搜索 Tool 的参数转换和 JSON 输出。"""

    # 创建符合商品仓储接口的假对象
    repository = Mock(spec=ProductRepository)

    # 模拟仓储返回一件商品
    repository.search.return_value = [
        Product(
            product_id="shirt-001",
            name="亚麻通勤衬衫",
            category="衬衫",
            price="299.00",
            colors=["白色", "浅蓝色"],
            sizes=["S", "M", "L"],
            in_stock=True,
        ),
    ]

    # 创建已经绑定假仓储的 Tool
    product_search = create_product_search_tool(
        repository,
    )

    # 使用类似 LLM Tool Call 的字典参数执行工具
    result = await product_search.ainvoke(
        {
            "query": "衬衫",
            "category": "衬衫",
            "max_price": "350.00",
            "limit": 5,
        }
    )

    # Pydantic 应将价格字符串转换成 Decimal
    repository.search.assert_called_once_with(
        query="衬衫",
        category="衬衫",
        max_price=Decimal("350.00"),
        limit=5,
    )

    # 将 Tool 返回的 JSON 字符串解析为 Python 数据
    product_data = json.loads(result)

    assert product_data == [
        {
            "product_id": "shirt-001",
            "name": "亚麻通勤衬衫",
            "category": "衬衫",
            "price": "299.00",
            "currency": "CNY",
            "colors": ["白色", "浅蓝色"],
            "sizes": ["S", "M", "L"],
            "in_stock": True,
        },
    ]


@pytest.mark.anyio
async def test_product_search_tool_returns_empty_json_list() -> None:
    """验证没有匹配商品时工具返回空 JSON 列表。"""

    # 创建假的商品仓库
    repository = Mock(spec=ProductRepository)

    # 模拟仓库没有找到任何匹配商品
    repository.search.return_value = []

    # 创建绑定假仓库的商品搜索工具
    product_search = create_product_search_tool(
        repository,
    )

    # 查询一个不存在的商品
    result = await product_search.ainvoke(
        {
            "query": "宇航服",
            "max_price": "100.00",
        },
    )

    # 验证工具正确地把查询条件传给仓库
    repository.search.assert_called_once_with(
        query="宇航服",
        category=None,
        max_price=Decimal("100.00"),
        limit=5,
    )

    # JSON 空数组解析后应该是 Python 空列表
    assert json.loads(result) == []