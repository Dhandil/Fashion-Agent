"""天气 API 输入结构测试。"""

import pytest
from pydantic import ValidationError

from app.api.schemas.weather import WeatherQueryInput


def test_weather_query_accepts_coordinate_pair() -> None:
    """验证设备经纬度可以与显示名称和日期一起提交。"""

    query = WeatherQueryInput(
        location="当前位置",
        target_date="2026-08-11",
        latitude=31.2304,
        longitude=121.4737,
    )

    assert query.latitude == 31.2304
    assert query.longitude == 121.4737


def test_weather_query_rejects_incomplete_coordinate_pair() -> None:
    """验证单独提供纬度时会在 API 边界被拒绝。"""

    with pytest.raises(ValidationError, match="必须同时提供"):
        WeatherQueryInput(
            location="当前位置",
            target_date="2026-08-11",
            latitude=31.2304,
        )
