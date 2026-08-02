"""对未通过检查的 Outfit 执行最多一次受限修正。"""

import json
import logging
from collections.abc import Callable
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import (
    HumanMessage,
    SystemMessage,
)

from app.agents.context import (
    get_current_turn_messages,
    get_current_turn_tool_records,
)
from app.agents.context_package import (
    DEFAULT_CONTEXT_MAX_CHARS,
    ContextCandidate,
    ContextPackage,
    ContextPriority,
    ContextSource,
    build_context_package,
)
from app.agents.prompts.outfit_correction import (
    OUTFIT_CORRECTION_SYSTEM_PROMPT,
)
from app.agents.schemas.outfit import OutfitGenerationResult
from app.agents.state.shopping import ShoppingAgentState
from app.agents.style_constraints import (
    get_effective_style_constraints,
    serialize_style_constraints,
)
from app.core.observability import log_event
from app.domain.entities.outfit import OutfitRecommendation
from app.domain.entities.weather import WeatherContext
from app.domain.policies.wardrobe_candidates import (
    select_eligible_wardrobe_records,
)

logger = logging.getLogger(__name__)


def _latest_user_request(state: ShoppingAgentState) -> str:
    """取得当前轮最后一条用户文本。"""

    for message in reversed(
        get_current_turn_messages(state["messages"]),
    ):
        if isinstance(message, HumanMessage) and isinstance(message.content, str):
            return message.content
    return ""


def _build_correction_context(
    state: ShoppingAgentState,
    max_chars: int,
) -> ContextPackage:
    """只为修正调用选择当前轮真实动态事实。"""

    candidates: list[ContextCandidate] = []
    requirement_analysis = state.get(
        "requirement_analysis",
    )
    if requirement_analysis is not None:
        candidates.append(
            ContextCandidate(
                key="requirement_analysis",
                source=(ContextSource.REQUIREMENT_ANALYSIS),
                priority=ContextPriority.CURRENT_FACT,
                content=(requirement_analysis.model_dump_json()),
                truncatable=False,
            ),
        )
    style_constraints = get_effective_style_constraints(
        state,
    )
    if not style_constraints.is_empty:
        candidates.append(
            ContextCandidate(
                key="effective_style_constraints",
                source=(ContextSource.EFFECTIVE_STYLE_CONSTRAINTS),
                priority=ContextPriority.CURRENT_FACT,
                content=serialize_style_constraints(
                    style_constraints,
                ),
                truncatable=False,
            ),
        )

    weather_records = get_current_turn_tool_records(
        state["messages"],
        "get_weather",
    )
    active_weather = state.get("weather_context")
    for record in reversed(weather_records):
        try:
            active_weather = WeatherContext.model_validate(record)
            break
        except ValueError:
            continue

    raw_wardrobe_records = get_current_turn_tool_records(
        state["messages"],
        "search_wardrobe",
    )
    wardrobe_records = select_eligible_wardrobe_records(
        raw_wardrobe_records,
        weather=active_weather,
        avoided_styles=(style_constraints.avoided_styles),
        avoided_colors=(style_constraints.avoided_colors),
        avoided_materials=(style_constraints.avoided_materials),
    ).eligible_records
    product_records = get_current_turn_tool_records(
        state["messages"],
        "search_products",
    )

    for source, records in (
        (ContextSource.WARDROBE, wardrobe_records),
        (ContextSource.PRODUCTS, product_records),
        (ContextSource.WEATHER_TOOL, weather_records),
    ):
        for index, record in enumerate(records):
            candidates.append(
                ContextCandidate(
                    key=f"{source.value}:{index}",
                    source=source,
                    priority=ContextPriority.CURRENT_FACT,
                    content=json.dumps(
                        record,
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                    truncatable=False,
                ),
            )

    weather = state.get("weather_context")
    if weather is not None:
        candidates.append(
            ContextCandidate(
                key="provided_weather",
                source=ContextSource.WEATHER,
                priority=ContextPriority.CURRENT_FACT,
                content=weather.model_dump_json(),
                truncatable=False,
            ),
        )

    return build_context_package(
        tuple(candidates),
        max_chars=max_chars,
    )


def _decode_values(
    package: ContextPackage,
    source: ContextSource,
) -> tuple[Any, ...]:
    """还原 Context Package 中保持完整的 JSON 事实。"""

    return tuple(json.loads(content) for content in package.contents_for(source))


def create_outfit_correction_node(
    model: BaseChatModel,
    context_max_chars: int = DEFAULT_CONTEXT_MAX_CHARS,
) -> Callable[[ShoppingAgentState], dict[str, Any]]:
    """创建绑定结构化模型的单次 Outfit 修正节点。"""

    structured_model = model.with_structured_output(
        OutfitGenerationResult,
        method="json_mode",
    )

    def correct_outfit(
        state: ShoppingAgentState,
    ) -> dict[str, Any]:
        """使用原方案、检查问题和当前轮事实尝试修正一次。"""

        original_recommendation = state.get(
            "outfit_recommendation",
        )
        report = state.get("outfit_feasibility_report")
        if original_recommendation is None or report is None:
            return {
                "outfit_correction_attempts": 1,
            }

        context_package = _build_correction_context(
            state,
            max_chars=context_max_chars,
        )
        diagnostics = context_package.diagnostics
        log_event(
            logger,
            "agent.context.built",
            purpose="outfit_correction",
            max_chars=diagnostics.max_chars,
            input_items=diagnostics.input_items,
            selected_items=diagnostics.selected_items,
            input_chars=diagnostics.input_chars,
            selected_chars=diagnostics.selected_chars,
            omitted_count=len(diagnostics.omitted_keys),
        )
        requirements = _decode_values(
            context_package,
            ContextSource.REQUIREMENT_ANALYSIS,
        )
        style_constraints = _decode_values(
            context_package,
            ContextSource.EFFECTIVE_STYLE_CONSTRAINTS,
        )
        provided_weather = _decode_values(
            context_package,
            ContextSource.WEATHER,
        )
        payload = {
            "output_schema": (OutfitGenerationResult.model_json_schema()),
            "current_request": _latest_user_request(state),
            "original_outfit": (
                original_recommendation.model_dump(
                    mode="json",
                )
            ),
            "validation_issues": [issue.model_dump(mode="json") for issue in report.issues],
            "requirement_analysis": (requirements[0] if requirements else None),
            "effective_style_constraints": (style_constraints[0] if style_constraints else None),
            "wardrobe_items": _decode_values(
                context_package,
                ContextSource.WARDROBE,
            ),
            "products": _decode_values(
                context_package,
                ContextSource.PRODUCTS,
            ),
            "weather_tool_results": _decode_values(
                context_package,
                ContextSource.WEATHER_TOOL,
            ),
            "provided_weather": (provided_weather[0] if provided_weather else None),
        }

        corrected_recommendation: OutfitRecommendation | None = None
        degraded = False
        try:
            raw_result = structured_model.invoke(
                [
                    SystemMessage(
                        content=(OUTFIT_CORRECTION_SYSTEM_PROMPT),
                    ),
                    HumanMessage(
                        content=json.dumps(
                            payload,
                            ensure_ascii=False,
                        ),
                    ),
                ],
            )
            corrected_recommendation = OutfitGenerationResult.model_validate(
                raw_result,
            ).outfit
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Outfit 受限修正失败，将保留原方案进入最终检查：%s",
                type(exc).__name__,
            )
            degraded = True

        log_event(
            logger,
            "agent.outfit.correction.completed",
            produced_outfit=(corrected_recommendation is not None),
            degraded=degraded,
        )
        return {
            # 修正失败或返回 null 时保留原方案，让第二次检查明确拒绝并返回原因。
            "outfit_recommendation": (corrected_recommendation or original_recommendation),
            "outfit_correction_attempts": 1,
        }

    return correct_outfit
