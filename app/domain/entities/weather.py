"""穿搭决策使用的天气领域实体。"""

from datetime import date, datetime
from enum import StrEnum
from typing import Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)


class WeatherDataSource(StrEnum):
    """天气数据的来源类型。"""

    # 用户或客户端明确提供
    USER_PROVIDED = "user_provided"

    # 授权的第三方天气 API
    API = "api"

    # MCP 天气服务
    MCP = "mcp"


class WeatherContext(BaseModel):
    """一次穿搭请求对应的天气事实。"""

    location: str = Field(
        min_length=1,
        max_length=200,
    )
    target_date: date
    condition: str | None = Field(
        default=None,
        max_length=100,
    )
    temperature_min_c: float | None = Field(
        default=None,
        ge=-100,
        le=100,
    )
    temperature_max_c: float | None = Field(
        default=None,
        ge=-100,
        le=100,
    )
    feels_like_c: float | None = Field(
        default=None,
        ge=-100,
        le=100,
    )
    precipitation_probability: int | None = Field(
        default=None,
        ge=0,
        le=100,
    )
    humidity_percent: int | None = Field(
        default=None,
        ge=0,
        le=100,
    )
    wind_speed_kph: float | None = Field(
        default=None,
        ge=0,
        le=500,
    )
    source: WeatherDataSource
    updated_at: datetime | None = None

    model_config = ConfigDict(
        frozen=True,
    )

    @model_validator(mode="after")
    def validate_weather_values(self) -> Self:
        """验证温度范围，并要求至少存在一项天气事实。"""

        if (
            self.temperature_min_c is not None
            and self.temperature_max_c is not None
            and self.temperature_min_c
            > self.temperature_max_c
        ):
            raise ValueError(
                "最低温度不能高于最高温度",
            )

        weather_facts = (
            self.condition,
            self.temperature_min_c,
            self.temperature_max_c,
            self.feels_like_c,
            self.precipitation_probability,
            self.humidity_percent,
            self.wind_speed_kph,
        )

        if all(
            value is None
            for value in weather_facts
        ):
            raise ValueError(
                "至少需要提供一项天气事实",
            )

        return self
