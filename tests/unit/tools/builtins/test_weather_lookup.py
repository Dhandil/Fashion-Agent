"""天气查询工具测试。"""

import json
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import WeatherProviderError
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
    provider.get_forecast.return_value = WeatherContext(
        location="上海",
        target_date="2026-08-01",
        condition="阵雨",
        temperature_min_c=26,
        temperature_max_c=33,
        precipitation_probability=70,
        source="api",
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


def test_weather_tool_exposes_query_location_date_and_optional_coordinates() -> None:
    """验证工具只暴露查询条件，不能伪造天气观测字段。"""

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
        "latitude",
        "longitude",
    }


@pytest.mark.anyio
async def test_weather_tool_passes_device_coordinates_to_provider() -> None:
    """验证前端设备定位坐标会原样交给天气 Provider。"""

    provider = AsyncMock(spec=WeatherProvider)
    provider.get_forecast.return_value = WeatherContext(
        location="当前位置",
        target_date="2026-08-11",
        condition="晴",
        source="api",
    )
    weather_tool = create_weather_lookup_tool(provider)

    await weather_tool.ainvoke(
        {
            "location": "当前位置",
            "target_date": "2026-08-11",
            "latitude": 31.2304,
            "longitude": 121.4737,
        },
    )

    provider.get_forecast.assert_awaited_once_with(
        location="当前位置",
        target_date=date(2026, 8, 11),
        latitude=31.2304,
        longitude=121.4737,
    )


@pytest.mark.anyio
async def test_weather_tool_degrades_provider_error() -> None:
    """验证外部天气服务失败时工具返回可识别错误，而不是中断 Agent。"""

    provider = AsyncMock(
        spec=WeatherProvider,
    )
    provider.get_forecast.side_effect = WeatherProviderError(
        "天气服务暂时不可用。",
    )
    weather_tool = create_weather_lookup_tool(
        provider,
    )

    with patch(
        "app.core.observability.log_event",
    ) as mocked_log_event:
        result = await weather_tool.ainvoke(
            {
                "location": "上海",
                "target_date": "2026-08-01",
            },
        )
    error = json.loads(result)

    assert error == {
        "error": "weather_unavailable",
        "message": "天气服务暂时不可用。",
        "location": "上海",
        "target_date": "2026-08-01",
    }
    events = {
        call.args[1]: call
        for call in mocked_log_event.call_args_list
    }
    assert events["provider.weather.failed"].kwargs[
        "error_type"
    ] == "WeatherProviderError"
    assert events["agent.tool.completed"].kwargs[
        "degraded"
    ] is True
    assert "location" not in events[
        "provider.weather.failed"
    ].kwargs
