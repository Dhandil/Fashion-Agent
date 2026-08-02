import json
import logging
from decimal import Decimal

from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, Field

from app.core.observability import observe_operation
from app.domain.repositories.product import ProductRepository

logger = logging.getLogger(__name__)


class ProductSearchInput(BaseModel):
    """商品搜索工具的输入参数。"""

    # 用户商品搜索关键词
    query: str = Field(
        min_length=1,
        max_length=200,
        description="商品搜索关键词",
    )

    # 可选商品品类
    category: str | None = Field(
        default=None,
        description="商品品类，例如衬衫或外套",
    )

    # 可选最高价格
    max_price: Decimal | None = Field(
        default=None,
        ge=0,
        description="用户可接受的最高价格",
    )

    # 最多返回的商品数量
    limit: int = Field(
        default=5,
        ge=1,
        le=20,
        description="最多返回的商品数量",
    )


def create_product_search_tool(
    repository: ProductRepository,
) -> BaseTool:
    """创建已经绑定商品仓储的搜索工具。"""

    @tool(
        args_schema=ProductSearchInput,
    )
    async def search_products(
        query: str,
        category: str | None = None,
        max_price: Decimal | None = None,
        limit: int = 5,
    ) -> str:
        """根据关键词、品类和预算搜索有库存的服装商品。"""

        with observe_operation(
            logger,
            "agent.tool",
            tool_name="search_products",
        ) as observation:
            # 异步等待商品仓库完成查询
            products = await repository.search(
                query=query,
                category=category,
                max_price=max_price,
                limit=limit,
            )

            # 将商品实体转换成可供模型读取的 JSON 字符串
            product_data = [
                product.model_dump(mode="json")
                for product in products
            ]
            observation.add_fields(
                result_count=len(product_data),
            )

            return json.dumps(
                product_data,
                ensure_ascii=False,
            )

    return search_products
