"""Open-Meteo 天气 Provider 测试。"""

from collections.abc import Callable
from datetime import date

import httpx
import pytest

from app.core.exceptions import (
    WeatherLocationNotFoundError,
    WeatherProviderError,
)
from app.domain.entities.weather import WeatherDataSource
from app.integrations.weather.open_meteo import (
    OpenMeteoWeatherProvider,
)

MockHandler = Callable[
    [httpx.Request],
    httpx.Response,
]


def _create_provider(
    handler: MockHandler,
    *,
    api_key: str | None = "test-key",
) -> tuple[
    OpenMeteoWeatherProvider,
    httpx.AsyncClient,
]:
    """创建使用 MockTransport 的 Provider，保证测试不会访问网络。"""

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
    )
    provider = OpenMeteoWeatherProvider(
        geocoding_base_url=("https://geocoding.example.test/"),
        forecast_base_url=("https://forecast.example.test/"),
        api_key=api_key,
        timeout_seconds=5,
        client=client,
    )
    return provider, client


@pytest.mark.anyio
async def test_provider_resolves_location_and_maps_daily_forecast() -> None:
    """验证地点搜索、预报参数和领域实体转换。"""

    requests: list[httpx.Request] = []

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        requests.append(request)
        if request.url.host == "geocoding.example.test":
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "name": "上海",
                            "admin1": "上海",
                            "country": "中国",
                            "latitude": 31.23,
                            "longitude": 121.47,
                            "timezone": "Asia/Shanghai",
                        },
                    ],
                },
            )

        return httpx.Response(
            200,
            json={
                "daily": {
                    "time": [
                        "2026-08-01",
                    ],
                    "weather_code": [
                        81,
                    ],
                    "temperature_2m_max": [
                        34.2,
                    ],
                    "temperature_2m_min": [
                        27.1,
                    ],
                    "apparent_temperature_mean": [
                        33.5,
                    ],
                    "precipitation_probability_max": [
                        70,
                    ],
                    "wind_speed_10m_max": [
                        18.4,
                    ],
                },
            },
        )

    provider, client = _create_provider(handler)
    try:
        weather = await provider.get_forecast(
            location=" 上海 ",
            target_date=date(
                2026,
                8,
                1,
            ),
        )
    finally:
        await client.aclose()

    assert weather.location == "上海，中国"
    assert weather.condition == "中等阵雨"
    assert weather.temperature_min_c == 27.1
    assert weather.temperature_max_c == 34.2
    assert weather.feels_like_c == 33.5
    assert weather.precipitation_probability == 70
    assert weather.wind_speed_kph == 18.4
    assert weather.source is WeatherDataSource.API
    assert weather.updated_at is not None

    assert len(requests) == 2
    geocoding_request, forecast_request = requests
    assert geocoding_request.url.params["name"] == "上海"
    assert geocoding_request.url.params["language"] == "zh"
    assert geocoding_request.url.params["apikey"] == "test-key"
    assert forecast_request.url.params["latitude"] == "31.23"
    assert forecast_request.url.params["longitude"] == "121.47"
    assert forecast_request.url.params["timezone"] == ("Asia/Shanghai")
    assert forecast_request.url.params["start_date"] == ("2026-08-01")
    assert forecast_request.url.params["end_date"] == ("2026-08-01")
    assert forecast_request.url.params["apikey"] == "test-key"


@pytest.mark.anyio
async def test_provider_rejects_unknown_location() -> None:
    """验证地点搜索没有结果时返回明确领域异常。"""

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            200,
            json={},
        )

    provider, client = _create_provider(handler)
    try:
        with pytest.raises(
            WeatherLocationNotFoundError,
            match="无法识别",
        ):
            await provider.get_forecast(
                location="不存在的地点",
                target_date=date(
                    2026,
                    8,
                    1,
                ),
            )
    finally:
        await client.aclose()


@pytest.mark.anyio
async def test_provider_normalizes_upstream_http_error() -> None:
    """验证上游状态码错误不会泄漏 httpx 异常到 Agent。"""

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            503,
            json={
                "error": True,
            },
        )

    provider, client = _create_provider(handler)
    try:
        with pytest.raises(
            WeatherProviderError,
            match="暂时不可用",
        ):
            await provider.get_forecast(
                location="上海",
                target_date=date(
                    2026,
                    8,
                    1,
                ),
            )
    finally:
        await client.aclose()


@pytest.mark.anyio
async def test_provider_rejects_incomplete_daily_forecast() -> None:
    """验证缺少目标字段的响应不会被包装成可信天气。"""

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        if request.url.host == "geocoding.example.test":
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "name": "上海",
                            "latitude": 31.23,
                            "longitude": 121.47,
                        },
                    ],
                },
            )
        return httpx.Response(
            200,
            json={
                "daily": {
                    "time": [
                        "2026-08-01",
                    ],
                },
            },
        )

    provider, client = _create_provider(
        handler,
        api_key=None,
    )
    try:
        with pytest.raises(
            WeatherProviderError,
            match="weather_code",
        ):
            await provider.get_forecast(
                location="上海",
                target_date=date(
                    2026,
                    8,
                    1,
                ),
            )
    finally:
        await client.aclose()
