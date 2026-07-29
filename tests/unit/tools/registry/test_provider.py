"""工具注册表提供者测试。"""

from app.tools.registry.provider import get_tool_registry


def test_get_tool_registry_registers_product_search_tool() -> None:
    """验证统一注册表包含商品搜索工具。"""

    # 清除缓存，确保本次测试重新装配工具注册表
    get_tool_registry.cache_clear()

    # 获取项目统一使用的工具注册表
    registry = get_tool_registry()

    # 获取已经注册的所有工具
    registered_tools = registry.list_tools()

    # 提取工具名称，便于检查目标工具是否存在
    tool_names = {
        registered_tool.name
        for registered_tool in registered_tools
    }

    # @tool 装饰的函数名会成为默认工具名称
    assert "search_products" in tool_names