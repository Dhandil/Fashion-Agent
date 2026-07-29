"""工具注册表的依赖提供模块。"""

from functools import lru_cache

from app.db.repositories.provider import (
    get_product_repository,
)
from app.tools.builtins.product_search import (
    create_product_search_tool,
)
from app.tools.registry.registry import ToolRegistry


@lru_cache
def get_tool_registry() -> ToolRegistry:
    """创建并缓存项目统一使用的工具注册表。"""

    # 创建一个空的工具注册表
    registry = ToolRegistry()

    # 获取已经加载商品数据的商品仓库
    product_repository = get_product_repository()

    # 创建商品搜索工具，并将其注册到注册表
    product_search_tool = create_product_search_tool(
        product_repository,
    )
    registry.register(product_search_tool)

    return registry