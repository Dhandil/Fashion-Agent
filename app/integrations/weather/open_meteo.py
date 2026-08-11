"""Open-Meteo 天气 Provider。"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime

import httpx

from app.core.exceptions import (
    WeatherLocationNotFoundError,
    WeatherProviderError,
)
from app.domain.entities.weather import (
    WeatherContext,
    WeatherDataSource,
)

_DAILY_VARIABLES = (
    "weather_code,temperature_2m_max,temperature_2m_min,"
    "apparent_temperature_mean,precipitation_probability_max,"
    "wind_speed_10m_max"
)

_WEATHER_CODE_DESCRIPTIONS = {
    0: "晴",
    1: "大致晴朗",
    2: "局部多云",
    3: "阴",
    45: "雾",
    48: "冻雾",
    51: "小毛毛雨",
    53: "中等毛毛雨",
    55: "强毛毛雨",
    56: "小冻毛毛雨",
    57: "强冻毛毛雨",
    61: "小雨",
    63: "中雨",
    65: "大雨",
    66: "小冻雨",
    67: "强冻雨",
    71: "小雪",
    73: "中雪",
    75: "大雪",
    77: "米雪",
    80: "小阵雨",
    81: "中等阵雨",
    82: "强阵雨",
    85: "小阵雪",
    86: "强阵雪",
    95: "雷暴",
    96: "雷暴伴小冰雹",
    99: "雷暴伴强冰雹",
}


@dataclass(
    frozen=True,
    slots=True,
)
class _ResolvedLocation:
    """地点搜索后供预报接口使用的标准化坐标。"""

    display_name: str
    latitude: float
    longitude: float
    timezone_name: str


class OpenMeteoWeatherProvider:
    """通过 Open-Meteo 地理编码和预报接口获取每日天气。"""

    def __init__(
        self,
        *,
        geocoding_base_url: str,
        forecast_base_url: str,
        api_key: str | None = None,
        timeout_seconds: float = 10.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        """保存连接参数；传入 client 便于测试时使用 MockTransport。"""

        self._geocoding_base_url = geocoding_base_url.rstrip("/")
        self._forecast_base_url = forecast_base_url.rstrip("/")
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._client = client

    async def get_forecast(
        self,
        location: str,
        target_date: date,
        *,
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> WeatherContext:
        """按地点名称或设备坐标查询目标日期的每日预报。"""

        normalized_location = location.strip()
        if not normalized_location:
            raise WeatherLocationNotFoundError(
                "天气查询地点不能为空。",
            )

        if (latitude is None) != (longitude is None):
            raise WeatherProviderError(
                "天气查询的纬度和经度必须同时提供。",
            )

        if self._client is not None:
            return await self._get_forecast_with_client(
                client=self._client,
                location=normalized_location,
                target_date=target_date,
                latitude=latitude,
                longitude=longitude,
            )

        # 默认每次调用使用独立客户端，避免 Provider 缓存后遗漏关闭连接
        async with httpx.AsyncClient(
            timeout=self._timeout_seconds,
        ) as client:
            return await self._get_forecast_with_client(
                client=client,
                location=normalized_location,
                target_date=target_date,
                latitude=latitude,
                longitude=longitude,
            )

    async def _get_forecast_with_client(
        self,
        *,
        client: httpx.AsyncClient,
        location: str,
        target_date: date,
        latitude: float | None,
        longitude: float | None,
    ) -> WeatherContext:
        """使用指定客户端完成两次请求并转换领域实体。"""

        if latitude is not None and longitude is not None:
            resolved_location = _ResolvedLocation(
                display_name=location,
                latitude=latitude,
                longitude=longitude,
                timezone_name="auto",
            )
        else:
            resolved_location = await self._resolve_location(
                client=client,
                location=location,
            )
        forecast = await self._request_json(
            client=client,
            url=f"{self._forecast_base_url}/v1/forecast",
            params={
                "latitude": resolved_location.latitude,
                "longitude": resolved_location.longitude,
                "daily": _DAILY_VARIABLES,
                "timezone": resolved_location.timezone_name,
                "start_date": target_date.isoformat(),
                "end_date": target_date.isoformat(),
                **self._api_key_params(),
            },
        )

        return self._build_weather_context(
            payload=forecast,
            location=resolved_location.display_name,
            target_date=target_date,
        )

    async def _resolve_location(
        self,
        *,
        client: httpx.AsyncClient,
        location: str,
    ) -> _ResolvedLocation:
        """使用地点搜索结果中的第一项生成坐标。"""

        payload = await self._request_json(
            client=client,
            url=f"{self._geocoding_base_url}/v1/search",
            params={
                "name": location,
                "count": 1,
                "format": "json",
                "language": "zh",
                **self._api_key_params(),
            },
        )
        results = payload.get("results")
        if not isinstance(results, list) or not results:
            raise WeatherLocationNotFoundError(
                f"无法识别天气查询地点：{location}",
            )

        first_result = results[0]
        if not isinstance(first_result, Mapping):
            raise WeatherProviderError(
                "天气地点服务返回了无效数据。",
            )

        name = self._required_text(
            first_result.get("name"),
            "name",
        )
        admin1 = self._optional_text(
            first_result.get("admin1"),
        )
        country = self._optional_text(
            first_result.get("country"),
        )
        location_parts = tuple(
            dict.fromkeys(
                part
                for part in (
                    name,
                    admin1,
                    country,
                )
                if part
            ),
        )

        return _ResolvedLocation(
            display_name="，".join(location_parts),
            latitude=self._required_number(
                first_result.get("latitude"),
                "latitude",
            ),
            longitude=self._required_number(
                first_result.get("longitude"),
                "longitude",
            ),
            timezone_name=(
                self._optional_text(
                    first_result.get("timezone"),
                )
                or "auto"
            ),
        )

    async def _request_json(
        self,
        *,
        client: httpx.AsyncClient,
        url: str,
        params: Mapping[
            str,
            str | int | float | bool | None,
        ],
    ) -> Mapping[str, object]:
        """统一处理网络、HTTP 状态码和 JSON 结构错误。"""

        try:
            response = await client.get(
                url,
                params=params,
            )
            response.raise_for_status()
            payload: object = response.json()
        except (
            httpx.HTTPError,
            ValueError,
        ) as exc:
            raise WeatherProviderError(
                "天气服务暂时不可用，请稍后重试或直接提供天气信息。",
            ) from exc

        if not isinstance(payload, Mapping):
            raise WeatherProviderError(
                "天气服务返回了无效数据。",
            )

        return payload

    def _build_weather_context(
        self,
        *,
        payload: Mapping[str, object],
        location: str,
        target_date: date,
    ) -> WeatherContext:
        """从 Open-Meteo daily 数组提取指定日期的一项数据。"""

        daily = payload.get("daily")
        if not isinstance(daily, Mapping):
            raise WeatherProviderError(
                "天气预报缺少每日数据。",
            )

        dates = daily.get("time")
        if not isinstance(dates, list):
            raise WeatherProviderError(
                "天气预报缺少日期数据。",
            )

        try:
            date_index = dates.index(
                target_date.isoformat(),
            )
        except ValueError as exc:
            raise WeatherProviderError(
                "天气服务未返回目标日期的预报。",
            ) from exc

        weather_code = round(
            self._daily_number(
                daily,
                "weather_code",
                date_index,
            ),
        )

        return WeatherContext(
            location=location,
            target_date=target_date,
            condition=(
                _WEATHER_CODE_DESCRIPTIONS.get(
                    weather_code,
                    f"未知天气（WMO {weather_code}）",
                )
            ),
            temperature_min_c=self._daily_number(
                daily,
                "temperature_2m_min",
                date_index,
            ),
            temperature_max_c=self._daily_number(
                daily,
                "temperature_2m_max",
                date_index,
            ),
            feels_like_c=self._daily_number(
                daily,
                "apparent_temperature_mean",
                date_index,
            ),
            precipitation_probability=round(
                self._daily_number(
                    daily,
                    "precipitation_probability_max",
                    date_index,
                ),
            ),
            wind_speed_kph=self._daily_number(
                daily,
                "wind_speed_10m_max",
                date_index,
            ),
            source=WeatherDataSource.API,
            updated_at=datetime.now(
                UTC,
            ),
        )

    @staticmethod
    def _daily_number(
        daily: Mapping[str, object],
        field_name: str,
        index: int,
    ) -> float:
        """读取 daily 中某个字段在目标日期的数字。"""

        values = daily.get(field_name)
        if not isinstance(values, list) or index >= len(values):
            raise WeatherProviderError(
                f"天气预报缺少字段：{field_name}",
            )

        return OpenMeteoWeatherProvider._required_number(
            values[index],
            field_name,
        )

    @staticmethod
    def _required_number(
        value: object,
        field_name: str,
    ) -> float:
        """读取必需数字，并拒绝 Python 中也属于 int 的布尔值。"""

        if isinstance(value, bool) or not isinstance(
            value,
            (
                int,
                float,
            ),
        ):
            raise WeatherProviderError(
                f"天气服务字段 {field_name} 不是有效数字。",
            )

        return float(value)

    @staticmethod
    def _required_text(
        value: object,
        field_name: str,
    ) -> str:
        """读取必需的非空文本。"""

        text = OpenMeteoWeatherProvider._optional_text(
            value,
        )
        if text is None:
            raise WeatherProviderError(
                f"天气服务字段 {field_name} 不是有效文本。",
            )
        return text

    @staticmethod
    def _optional_text(
        value: object,
    ) -> str | None:
        """把可选文本去除首尾空格，空文本视为缺失。"""

        if not isinstance(value, str):
            return None
        return value.strip() or None

    def _api_key_params(self) -> dict[str, str]:
        """只在配置密钥时向 Open-Meteo 请求添加 apikey。"""

        if self._api_key is None:
            return {}
        return {
            "apikey": self._api_key,
        }
