"""聊天请求使用的天气数据结构。"""

from datetime import date, datetime
from typing import Self

from pydantic import (
    BaseModel,
    Field,
    model_validator,
)


class WeatherQueryInput(BaseModel):
    """前端请求实时天气时提供的地点和日期。"""

    location: str = Field(min_length=1, max_length=200)
    target_date: date


class WeatherContextInput(BaseModel):
    """由用户或客户端明确提供的当前天气上下文。"""

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
    updated_at: datetime | None = None

    @model_validator(mode="after")
    def validate_weather_values(self) -> Self:
        """在进入路由前验证温度范围和天气事实。"""

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
