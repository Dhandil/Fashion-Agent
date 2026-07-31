"""天气上下文领域实体测试。"""

from datetime import date

import pytest
from pydantic import ValidationError

from app.domain.entities.weather import (
    WeatherContext,
    WeatherDataSource,
)


def test_weather_context_validates_and_converts_values() -> None:
    """验证日期、温度、降雨和来源会转换为领域类型。"""

    weather = WeatherContext(
        location="上海",
        target_date="2026-08-01",
        condition="阵雨",
        temperature_min_c=26,
        temperature_max_c=33,
        precipitation_probability=70,
        source="user_provided",
    )

    assert weather.target_date == date(
        2026,
        8,
        1,
    )
    assert (
        weather.source
        is WeatherDataSource.USER_PROVIDED
    )
    assert weather.precipitation_probability == 70


def test_weather_context_rejects_reversed_temperature_range() -> None:
    """验证最低温度不能高于最高温度。"""

    with pytest.raises(
        ValidationError,
        match="最低温度不能高于最高温度",
    ):
        WeatherContext(
            location="上海",
            target_date="2026-08-01",
            temperature_min_c=35,
            temperature_max_c=25,
            source="api",
        )


def test_weather_context_requires_weather_fact() -> None:
    """验证只有地点和日期时不能伪装成天气结果。"""

    with pytest.raises(
        ValidationError,
        match="至少需要提供一项天气事实",
    ):
        WeatherContext(
            location="上海",
            target_date="2026-08-01",
            source="mcp",
        )

