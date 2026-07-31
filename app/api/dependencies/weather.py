"""天气服务依赖。"""

from typing import Annotated

from fastapi import Depends

from app.domain.providers.weather import WeatherProvider
from app.integrations.weather.provider import (
    get_weather_provider,
)

# Provider 可以关闭；关闭时请求级 Agent 不会注册 get_weather 工具
WeatherProviderDependency = Annotated[
    WeatherProvider | None,
    Depends(get_weather_provider),
]
