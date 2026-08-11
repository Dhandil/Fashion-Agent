"""天气查询 Agent 工具。"""

import json
import logging
from datetime import date
from typing import Self

from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, Field, model_validator

from app.core.exceptions import WeatherProviderError
from app.core.observability import observe_operation
from app.domain.policies.weather import (
    build_weather_outfit_guidance,
)
from app.domain.providers.weather import WeatherProvider

logger = logging.getLogger(__name__)


class WeatherLookupInput(BaseModel):
    """天气工具允许模型提供的输入参数。"""

    location: str = Field(
        min_length=1,
        max_length=200,
        description="需要查询天气的城市或地点",
    )
    target_date: date = Field(
        description="需要查询的日期，格式为 YYYY-MM-DD",
    )
    latitude: float | None = Field(
        default=None,
        ge=-90,
        le=90,
        description="设备定位提供的纬度；必须与经度同时提供",
    )
    longitude: float | None = Field(
        default=None,
        ge=-180,
        le=180,
        description="设备定位提供的经度；必须与纬度同时提供",
    )

    @model_validator(mode="after")
    def validate_coordinates(self) -> Self:
        """拒绝只有纬度或只有经度的不完整设备定位。"""

        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("纬度和经度必须同时提供")
        return self


def create_weather_lookup_tool(
    provider: WeatherProvider,
) -> BaseTool:
    """创建绑定具体天气 Provider 的查询工具。"""

    @tool(
        args_schema=WeatherLookupInput,
    )
    async def get_weather(
        location: str,
        target_date: date,
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> str:
        """查询指定地点和日期的天气事实。"""

        with observe_operation(
            logger,
            "agent.tool",
            tool_name="get_weather",
        ) as tool_observation:
            try:
                with observe_operation(
                    logger,
                    "provider.weather",
                    provider_type=(type(provider).__name__),
                ):
                    if latitude is not None and longitude is not None:
                        weather = await provider.get_forecast(
                            location=location,
                            target_date=target_date,
                            latitude=latitude,
                            longitude=longitude,
                        )
                    else:
                        weather = await provider.get_forecast(
                            location=location,
                            target_date=target_date,
                        )
            except WeatherProviderError as exc:
                # 外部服务失败不应中断整次穿搭对话；对象结构也不会被当成天气记录
                logger.warning(
                    "天气查询失败，已降级为无实时天气：%s",
                    type(exc).__name__,
                )
                tool_observation.add_fields(
                    degraded=True,
                    result_count=0,
                )
                return json.dumps(
                    {
                        "error": "weather_unavailable",
                        "message": str(exc),
                        "location": location,
                        "target_date": target_date.isoformat(),
                    },
                    ensure_ascii=False,
                )

            weather_record = weather.model_dump(
                mode="json",
            )
            weather_record["outfit_guidance"] = build_weather_outfit_guidance(
                weather,
            )
            tool_observation.add_fields(
                degraded=False,
                result_count=1,
            )

            # 使用列表结构，便于复用 Agent 当前的工具结果解析逻辑
            return json.dumps(
                [
                    weather_record,
                ],
                ensure_ascii=False,
            )

    return get_weather
