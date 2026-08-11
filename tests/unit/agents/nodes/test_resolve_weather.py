"""结构化天气查询节点测试。"""

import asyncio
import json
from unittest.mock import AsyncMock, Mock

from langchain_core.tools import BaseTool

from app.agents.nodes.resolve_weather import create_weather_query_node


def test_weather_query_node_calls_weather_tool() -> None:
    """地点和日期齐全时，节点应调用天气工具并写入天气上下文。"""

    weather_tool = Mock(spec=BaseTool)
    weather_tool.ainvoke = AsyncMock(
        return_value=json.dumps(
            [
                {
                    "location": "上海",
                    "target_date": "2026-08-09",
                    "condition": "晴",
                    "temperature_min_c": 25,
                    "temperature_max_c": 33,
                    "source": "api",
                },
            ],
        ),
    )
    node = create_weather_query_node(weather_tool)

    result = asyncio.run(
        node(
            {
                "messages": [],
                "weather_query": {
                    "location": "上海",
                    "target_date": "2026-08-09",
                },
            },
        ),
    )

    weather_tool.ainvoke.assert_awaited_once_with(
        {
            "location": "上海",
            "target_date": "2026-08-09",
        },
    )
    assert result["weather_context"].source.value == "api"
    assert result["weather_context"].temperature_max_c == 33


def test_weather_query_node_is_noop_without_tool() -> None:
    """未启用天气 Provider 时，节点应保持同步空操作。"""

    node = create_weather_query_node(None)
    assert node({"messages": []}) == {}


def test_weather_query_node_forwards_device_coordinates() -> None:
    """验证结构化天气节点不会丢失浏览器提供的经纬度。"""

    weather_tool = Mock(spec=BaseTool)
    weather_tool.ainvoke = AsyncMock(
        return_value=json.dumps(
            [
                {
                    "location": "当前位置",
                    "target_date": "2026-08-11",
                    "condition": "晴",
                    "source": "api",
                },
            ],
        ),
    )
    node = create_weather_query_node(weather_tool)
    query = {
        "location": "当前位置",
        "target_date": "2026-08-11",
        "latitude": 31.2304,
        "longitude": 121.4737,
    }

    asyncio.run(node({"messages": [], "weather_query": query}))

    weather_tool.ainvoke.assert_awaited_once_with(query)
