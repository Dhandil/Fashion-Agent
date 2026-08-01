"""结构化 Outfit 的确定性可执行性检查节点。"""

import logging
from typing import Any

from langchain_core.messages import AIMessage

from app.agents.context import get_current_turn_tool_records
from app.agents.state.shopping import ShoppingAgentState
from app.core.observability import log_event
from app.domain.entities.outfit_validation import (
    OutfitIssueSeverity,
)
from app.domain.entities.weather import WeatherContext
from app.domain.policies.outfit_feasibility import (
    evaluate_outfit_feasibility,
)

logger = logging.getLogger(__name__)


def _latest_tool_weather(
    state: ShoppingAgentState,
) -> WeatherContext | None:
    """从当前轮天气工具结果中读取最后一条有效事实。"""

    weather_records = get_current_turn_tool_records(
        state["messages"],
        "get_weather",
    )
    for record in reversed(weather_records):
        try:
            return WeatherContext.model_validate(record)
        except ValueError:
            continue
    return None


def validate_outfit(
    state: ShoppingAgentState,
) -> dict[str, Any]:
    """检查本轮推荐；错误会阻止不可靠 Outfit 进入 API 响应。"""

    recommendation = state.get(
        "outfit_recommendation",
    )
    if recommendation is None:
        return {
            "outfit_feasibility_report": None,
        }

    wardrobe_records = get_current_turn_tool_records(
        state["messages"],
        "search_wardrobe",
    )
    product_records = get_current_turn_tool_records(
        state["messages"],
        "search_products",
    )
    active_weather = _latest_tool_weather(state) or state.get("weather_context")
    report = evaluate_outfit_feasibility(
        recommendation,
        wardrobe_records=wardrobe_records,
        product_records=product_records,
        weather=active_weather,
        requirement_analysis=state.get(
            "requirement_analysis",
        ),
    )
    error_issues = tuple(
        issue for issue in report.issues if issue.severity is OutfitIssueSeverity.ERROR
    )
    log_event(
        logger,
        "agent.outfit.validated",
        is_executable=report.is_executable,
        issue_count=len(report.issues),
        error_count=len(error_issues),
        warning_count=(len(report.issues) - len(error_issues)),
        issue_codes=[issue.code.value for issue in report.issues],
    )

    if report.is_executable:
        return {
            "outfit_feasibility_report": report,
        }

    # 首次失败只保存报告，由路由决定是否执行唯一一次受限修正。
    if state.get("outfit_correction_attempts", 0) == 0:
        return {
            "outfit_feasibility_report": report,
        }

    error_summary = "；".join(issue.message for issue in error_issues[:3])
    return {
        "outfit_recommendation": None,
        "outfit_feasibility_report": report,
        "messages": [
            AIMessage(
                content=(
                    "刚才的方案没有通过可执行性检查，"
                    "因此暂不作为最终穿搭返回。"
                    f"主要问题：{error_summary}"
                ),
            ),
        ],
    }
