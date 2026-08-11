"""天气外部能力接口。"""

from datetime import date
from typing import Protocol

from app.domain.entities.weather import WeatherContext


class WeatherProvider(Protocol):
    """定义天气 API 或 MCP 适配器必须提供的能力。"""

    async def get_forecast(
        self,
        location: str,
        target_date: date,
        *,
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> WeatherContext:
        """按地点名称或设备坐标查询指定日期的天气。"""

        ...
