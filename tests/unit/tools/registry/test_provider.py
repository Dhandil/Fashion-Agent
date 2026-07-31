"""工具注册表提供者测试。"""

from unittest.mock import Mock

from app.domain.providers.weather import WeatherProvider
from app.domain.repositories.wardrobe import (
    WardrobeRepository,
)
from app.tools.registry.provider import (
    create_request_tool_registry,
    get_tool_registry,
)


def test_get_tool_registry_registers_product_search_tool() -> None:
    """验证统一注册表包含商品搜索工具。"""

    # 清除缓存，确保本次测试重新装配工具注册表
    get_tool_registry.cache_clear()

    # 获取项目统一使用的工具注册表
    registry = get_tool_registry()

    # 获取已经注册的所有工具
    registered_tools = registry.list_tools()

    # 提取工具名称，便于检查目标工具是否存在
    tool_names = {registered_tool.name for registered_tool in registered_tools}

    # @tool 装饰的函数名会成为默认工具名称
    assert "search_products" in tool_names


def test_request_registry_adds_user_scoped_wardrobe_tool() -> None:
    """验证请求注册表同时包含共享工具和当前用户衣橱工具。"""

    wardrobe_repository = Mock(
        spec=WardrobeRepository,
    )

    request_registry = create_request_tool_registry(
        wardrobe_repository=wardrobe_repository,
        user_id="user-001",
    )

    tools_by_name = {
        registered_tool.name: registered_tool for registered_tool in request_registry.list_tools()
    }

    assert set(tools_by_name) == {
        "search_products",
        "search_wardrobe",
    }

    wardrobe_tool = tools_by_name["search_wardrobe"]
    assert wardrobe_tool.args_schema is not None

    # 模型只能选择筛选条件，不能自行指定用户身份
    assert "user_id" not in (wardrobe_tool.args_schema.model_fields)


def test_request_registry_adds_weather_tool_when_configured() -> None:
    """验证只有提供 Weather Provider 时才注册天气工具。"""

    wardrobe_repository = Mock(
        spec=WardrobeRepository,
    )
    weather_provider = Mock(
        spec=WeatherProvider,
    )

    request_registry = create_request_tool_registry(
        wardrobe_repository=wardrobe_repository,
        user_id="user-001",
        weather_provider=weather_provider,
    )
    tool_names = {
        registered_tool.name
        for registered_tool
        in request_registry.list_tools()
    }

    assert tool_names == {
        "search_products",
        "search_wardrobe",
        "get_weather",
    }
