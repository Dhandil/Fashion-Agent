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
    ) -> WeatherContext:
        """查询指定地点和日期的天气。"""

        ...
