"""天气 Provider 配置装配测试。"""

from unittest.mock import patch

import pytest

from app.core.config import Settings
from app.core.exceptions import ConfigurationError
from app.integrations.weather.open_meteo import (
    OpenMeteoWeatherProvider,
)
from app.integrations.weather.provider import (
    get_weather_provider,
)


def test_provider_factory_returns_none_when_disabled() -> None:
    """验证默认关闭天气能力时不创建外部适配器。"""

    settings = Settings(
        _env_file=None,
        weather_provider_backend="disabled",
    )
    get_weather_provider.cache_clear()

    with patch(
        "app.integrations.weather.provider.get_settings",
        return_value=settings,
    ):
        provider = get_weather_provider()

    assert provider is None
    get_weather_provider.cache_clear()


def test_provider_factory_builds_open_meteo_adapter() -> None:
    """验证配置启用后创建 Open-Meteo 适配器。"""

    settings = Settings(
        _env_file=None,
        weather_provider_backend="open_meteo",
        weather_geocoding_base_url=("https://geocoding.example.test"),
        weather_forecast_base_url=("https://forecast.example.test"),
        weather_api_key="test-key",
        weather_timeout_seconds=12,
    )
    get_weather_provider.cache_clear()

    with patch(
        "app.integrations.weather.provider.get_settings",
        return_value=settings,
    ):
        provider = get_weather_provider()

    assert isinstance(
        provider,
        OpenMeteoWeatherProvider,
    )
    get_weather_provider.cache_clear()


def test_provider_factory_requires_key_in_production() -> None:
    """验证生产环境不会误用仅限非商业原型的公共端点。"""

    settings = Settings(
        _env_file=None,
        app_env="production",
        weather_provider_backend="open_meteo",
        weather_api_key=None,
    )
    get_weather_provider.cache_clear()

    with (
        patch(
            "app.integrations.weather.provider.get_settings",
            return_value=settings,
        ),
        pytest.raises(
            ConfigurationError,
            match="WEATHER_API_KEY",
        ),
    ):
        get_weather_provider()

    get_weather_provider.cache_clear()
