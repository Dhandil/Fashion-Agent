"""天气查询工具测试。"""

import json
from datetime import date
from unittest.mock import AsyncMock

import pytest

from app.domain.entities.weather import WeatherContext
from app.domain.providers.weather import WeatherProvider
from app.tools.builtins.weather_lookup import (
    create_weather_lookup_tool,
)


@pytest.mark.anyio
async def test_weather_tool_returns_provider_result() -> None:
    """验证工具使用模型参数调用 Provider 并返回 JSON。"""

    provider = AsyncMock(
        spec=WeatherProvider,
    )
    provider.get_forecast.return_value = (
        WeatherContext(
            location="上海",
            target_date="2026-08-01",
            condition="阵雨",
            temperature_min_c=26,
            temperature_max_c=33,
            precipitation_probability=70,
            source="api",
        )
    )
    weather_tool = create_weather_lookup_tool(
        provider,
    )

    result = await weather_tool.ainvoke(
        {
            "location": "上海",
            "target_date": "2026-08-01",
        },
    )
    records = json.loads(result)

    provider.get_forecast.assert_awaited_once_with(
        location="上海",
        target_date=date(
            2026,
            8,
            1,
        ),
    )
    assert records[0]["condition"] == "阵雨"
    assert records[0]["source"] == "api"
    assert records[0]["target_date"] == "2026-08-01"


def test_weather_tool_exposes_only_location_and_date() -> None:
    """验证模型不能指定天气来源或伪造观测字段。"""

    provider = AsyncMock(
        spec=WeatherProvider,
    )
    weather_tool = create_weather_lookup_tool(
        provider,
    )

    assert weather_tool.args_schema is not None
    assert set(
        weather_tool.args_schema.model_fields,
    ) == {
        "location",
        "target_date",
    }

