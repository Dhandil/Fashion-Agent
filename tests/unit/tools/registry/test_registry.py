import pytest
from langchain_core.tools import tool

from app.core.exceptions import ToolRegistryError
from app.tools.registry.registry import ToolRegistry


@tool
def sample_search(query: str) -> str:
    """根据关键词返回测试搜索结果。"""

    return f"搜索结果：{query}"


def test_registry_registers_and_gets_tool() -> None:
    """验证工具可以注册并按名称获取。"""

    registry = ToolRegistry()

    registry.register(sample_search)

    assert registry.get("sample_search") is sample_search
    assert registry.list_tools() == (sample_search,)


def test_registry_rejects_duplicate_tool() -> None:
    """验证同名工具不能重复注册。"""

    registry = ToolRegistry()
    registry.register(sample_search)

    with pytest.raises(
        ToolRegistryError,
        match="工具 sample_search 已经注册",
    ):
        registry.register(sample_search)


def test_registry_raises_for_unknown_tool() -> None:
    """验证查询不存在的工具时抛出明确异常。"""

    registry = ToolRegistry()

    with pytest.raises(
        ToolRegistryError,
        match="找不到工具 missing_tool",
    ):
        registry.get("missing_tool")