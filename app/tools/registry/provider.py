"""工具注册表的依赖提供模块。"""

from functools import lru_cache

from app.db.repositories.provider import (
    get_product_repository,
)
from app.domain.repositories.wardrobe import (
    WardrobeRepository,
)
from app.tools.builtins.product_search import (
    create_product_search_tool,
)
from app.tools.builtins.wardrobe_search import (
    create_wardrobe_search_tool,
)
from app.tools.registry.registry import ToolRegistry


@lru_cache
def get_tool_registry() -> ToolRegistry:
    """创建并缓存不包含请求状态的共享工具注册表。"""

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


def create_request_tool_registry(
    wardrobe_repository: WardrobeRepository,
    user_id: str,
) -> ToolRegistry:
    """为当前用户创建包含请求级衣橱工具的注册表。"""

    # 每次请求创建新注册表，避免把数据库 Session 缓存在全局对象中
    request_registry = ToolRegistry()

    # 共享工具本身不持有当前用户或请求级数据库 Session，可以安全复用
    for shared_tool in get_tool_registry().list_tools():
        request_registry.register(shared_tool)

    # 衣橱工具通过闭包绑定当前请求的仓库和用户身份
    wardrobe_search_tool = create_wardrobe_search_tool(
        repository=wardrobe_repository,
        user_id=user_id,
    )
    request_registry.register(wardrobe_search_tool)

    return request_registry
