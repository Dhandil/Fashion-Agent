"""天气 Provider 的配置装配。"""

from functools import lru_cache

from app.core.config import get_settings
from app.core.exceptions import ConfigurationError
from app.domain.providers.weather import WeatherProvider
from app.integrations.weather.open_meteo import (
    OpenMeteoWeatherProvider,
)


@lru_cache
def get_weather_provider() -> WeatherProvider | None:
    """根据配置创建可选天气 Provider。"""

    settings = get_settings()
    if settings.weather_provider_backend == "disabled":
        return None

    api_key = (
        settings.weather_api_key.get_secret_value()
        if settings.weather_api_key is not None
        else None
    )

    # Open-Meteo 免费公共端点仅允许非商业用途，生产启用时必须显式配置密钥
    if settings.app_env.lower() == "production" and api_key is None:
        raise ConfigurationError(
            "生产环境启用 Open-Meteo 时必须配置 WEATHER_API_KEY，"
            "并使用符合授权要求的客户或自托管端点。",
        )

    return OpenMeteoWeatherProvider(
        geocoding_base_url=(settings.weather_geocoding_base_url),
        forecast_base_url=(settings.weather_forecast_base_url),
        api_key=api_key,
        timeout_seconds=(settings.weather_timeout_seconds),
    )
