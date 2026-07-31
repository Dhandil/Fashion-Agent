"""天气查询 Agent 工具。"""

import json
from datetime import date

from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, Field

from app.domain.providers.weather import WeatherProvider


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
    ) -> str:
        """查询指定地点和日期的天气事实。"""

        weather = await provider.get_forecast(
            location=location,
            target_date=target_date,
        )

        # 使用列表结构，便于复用 Agent 当前的工具结果解析逻辑
        return json.dumps(
            [
                weather.model_dump(
                    mode="json",
                ),
            ],
            ensure_ascii=False,
        )

    return get_weather
