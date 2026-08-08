"""解析前端明确提供的天气查询，并调用已注册天气工具。"""

import json
import logging
from collections.abc import Callable
from typing import Any

from langchain_core.tools import BaseTool

from app.agents.state.shopping import ShoppingAgentState
from app.core.observability import log_event
from app.domain.entities.weather import WeatherContext

logger = logging.getLogger(__name__)


def create_weather_query_node(
    weather_tool: BaseTool | None,
) -> Callable[[ShoppingAgentState], Any]:
    """创建一个只在前端提交结构化天气查询时运行的节点。"""

    if weather_tool is None:
        def skip_weather_query(
            state: ShoppingAgentState,
        ) -> dict[str, Any]:
            del state
            return {}

        return skip_weather_query

    async def resolve_weather_query(
        state: ShoppingAgentState,
    ) -> dict[str, WeatherContext]:
        query = state.get("weather_query")
        if not query:
            return {}

        try:
            raw_result = await weather_tool.ainvoke(query)
            records = json.loads(str(raw_result))
            if not isinstance(records, list) or not records:
                raise ValueError("天气工具没有返回有效记录")
            weather = WeatherContext.model_validate(records[0])
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "结构化天气查询失败，继续使用无实时天气模式：%s",
                type(exc).__name__,
            )
            log_event(
                logger,
                "agent.weather_query.failed",
                error_type=type(exc).__name__,
            )
            return {}

        log_event(
            logger,
            "agent.weather_query.completed",
            location=weather.location,
            target_date=weather.target_date.isoformat(),
        )
        return {"weather_context": weather}

    return resolve_weather_query
