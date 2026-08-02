"""结构化 Outfit 推荐生成节点。"""

import json
import logging
from collections.abc import Callable
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
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
from app.agents.prompts.outfit import (
    OUTFIT_GENERATION_SYSTEM_PROMPT,
)
from app.agents.schemas.outfit import (
    OutfitGenerationResult,
)
from app.agents.state.shopping import ShoppingAgentState
from app.agents.style_constraints import (
    get_effective_style_constraints,
    serialize_style_constraints,
)
from app.core.observability import log_event
from app.domain.entities.outfit import (
    OutfitRecommendation,
)
from app.domain.entities.weather import WeatherContext
from app.domain.policies.wardrobe_candidates import (
    select_eligible_wardrobe_records,
)
from app.domain.policies.weather import (
    build_weather_outfit_guidance,
)

logger = logging.getLogger(__name__)


def _get_latest_text(
    state: ShoppingAgentState,
    message_type: type[HumanMessage] | type[AIMessage],
) -> str:
    """取得当前轮次指定类型消息的最新文本内容。"""

    for message in reversed(
        get_current_turn_messages(state["messages"]),
    ):
        if isinstance(message, message_type) and isinstance(message.content, str):
            return message.content

    return ""


def _get_weather_from_records(
    records: tuple[dict[str, Any], ...],
) -> WeatherContext | None:
    """从当前轮工具记录中取得最后一条有效天气。"""

    for record in reversed(records):
        try:
            return WeatherContext.model_validate(
                record,
            )
        except ValueError:
            continue

    return None


def _create_generation_context_package(
    state: ShoppingAgentState,
    wardrobe_records: tuple[dict[str, Any], ...],
    product_records: tuple[dict[str, Any], ...],
    weather_records: tuple[dict[str, Any], ...],
    active_weather: WeatherContext | None,
    max_chars: int,
) -> ContextPackage:
    """装配结构化 Outfit 生成所需的受控上下文。"""

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

    # 本轮工具事实逐条作为原子项加入，超出预算时整条舍弃，避免破坏 JSON。
    for source, records in (
        (ContextSource.WEATHER_TOOL, weather_records),
        (ContextSource.WARDROBE, wardrobe_records),
        (ContextSource.PRODUCTS, product_records),
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

    provided_weather = state.get("weather_context")
    if provided_weather is not None:
        candidates.append(
            ContextCandidate(
                key="provided_weather",
                source=ContextSource.WEATHER,
                priority=ContextPriority.CURRENT_FACT,
                content=provided_weather.model_dump_json(),
                truncatable=False,
            ),
        )

    if active_weather is not None:
        weather_guidance = build_weather_outfit_guidance(
            active_weather,
        )
        if weather_guidance:
            candidates.append(
                ContextCandidate(
                    key="weather_guidance",
                    source=ContextSource.WEATHER_GUIDANCE,
                    priority=ContextPriority.CURRENT_FACT,
                    content=json.dumps(
                        weather_guidance,
                        ensure_ascii=False,
                    ),
                    truncatable=False,
                ),
            )

    style_profile = state.get(
        "style_profile_context",
        "",
    )
    if style_profile:
        candidates.append(
            ContextCandidate(
                key="style_profile",
                source=ContextSource.STYLE_PROFILE,
                priority=ContextPriority.EXPLICIT_MEMORY,
                content=style_profile,
            ),
        )

    previous_outfit = state.get(
        "previous_outfit_recommendation",
    )
    if previous_outfit is not None:
        candidates.append(
            ContextCandidate(
                key="previous_outfit",
                source=ContextSource.PREVIOUS_OUTFIT,
                priority=ContextPriority.EXPLICIT_MEMORY,
                content=previous_outfit.model_dump_json(),
                truncatable=False,
            ),
        )

    for key, source, content in (
        (
            "outfit_feedback",
            ContextSource.OUTFIT_FEEDBACK,
            state.get("outfit_feedback_context", ""),
        ),
        (
            "recent_outfits",
            ContextSource.RECENT_OUTFITS,
            state.get("recent_outfits_context", ""),
        ),
    ):
        if content:
            candidates.append(
                ContextCandidate(
                    key=key,
                    source=source,
                    priority=ContextPriority.HISTORICAL_MEMORY,
                    content=content,
                ),
            )

    knowledge = state.get("knowledge_context", "")
    if knowledge:
        candidates.append(
            ContextCandidate(
                key="knowledge",
                source=ContextSource.KNOWLEDGE,
                priority=ContextPriority.KNOWLEDGE,
                content=knowledge,
            ),
        )

    return build_context_package(
        tuple(candidates),
        max_chars=max_chars,
    )


def _decode_context_values(
    package: ContextPackage,
    source: ContextSource,
) -> tuple[Any, ...]:
    """把未截断的 JSON 上下文还原为结构化值。"""

    return tuple(json.loads(content) for content in package.contents_for(source))


def create_outfit_generation_node(
    model: BaseChatModel,
    context_max_chars: int = DEFAULT_CONTEXT_MAX_CHARS,
) -> Callable[
    [ShoppingAgentState],
    dict[str, OutfitRecommendation | None],
]:
    """创建使用结构化模型输出 Outfit 的节点。"""

    # JSON Mode 不强制 tool_choice，兼容 DeepSeek Thinking Mode
    structured_model = model.with_structured_output(
        OutfitGenerationResult,
        method="json_mode",
    )

    def generate_outfit(
        state: ShoppingAgentState,
    ) -> dict[str, OutfitRecommendation | None]:
        """根据当前轮次工具结果生成并校验结构化 Outfit。"""

        raw_wardrobe_records = get_current_turn_tool_records(
            state["messages"],
            "search_wardrobe",
        )
        product_records = get_current_turn_tool_records(
            state["messages"],
            "search_products",
        )
        weather_records = get_current_turn_tool_records(
            state["messages"],
            "get_weather",
        )
        weather_context = state.get(
            "weather_context",
        )
        active_weather = (
            _get_weather_from_records(
                weather_records,
            )
            or weather_context
        )
        style_constraints = get_effective_style_constraints(state)
        wardrobe_selection = select_eligible_wardrobe_records(
            raw_wardrobe_records,
            weather=active_weather,
            avoided_styles=(style_constraints.avoided_styles),
            avoided_colors=(style_constraints.avoided_colors),
            avoided_materials=(style_constraints.avoided_materials),
        )
        wardrobe_records = wardrobe_selection.eligible_records

        context_package = _create_generation_context_package(
            state=state,
            wardrobe_records=wardrobe_records,
            product_records=product_records,
            weather_records=weather_records,
            active_weather=active_weather,
            max_chars=context_max_chars,
        )
        diagnostics = context_package.diagnostics
        log_event(
            logger,
            "agent.context.built",
            purpose="outfit_generation",
            max_chars=diagnostics.max_chars,
            input_items=diagnostics.input_items,
            selected_items=diagnostics.selected_items,
            input_chars=diagnostics.input_chars,
            selected_chars=diagnostics.selected_chars,
            duplicate_count=len(diagnostics.duplicate_keys),
            omitted_count=len(diagnostics.omitted_keys),
            truncated_count=len(diagnostics.truncated_keys),
            excluded_wardrobe_count=len(
                wardrobe_selection.exclusions,
            ),
        )

        decoded_weather = _decode_context_values(
            context_package,
            ContextSource.WEATHER,
        )
        decoded_weather_tool_results = _decode_context_values(
            context_package,
            ContextSource.WEATHER_TOOL,
        )
        decoded_guidance = _decode_context_values(
            context_package,
            ContextSource.WEATHER_GUIDANCE,
        )
        decoded_previous_outfit = _decode_context_values(
            context_package,
            ContextSource.PREVIOUS_OUTFIT,
        )
        decoded_requirements = _decode_context_values(
            context_package,
            ContextSource.REQUIREMENT_ANALYSIS,
        )
        decoded_style_constraints = _decode_context_values(
            context_package,
            ContextSource.EFFECTIVE_STYLE_CONSTRAINTS,
        )

        generation_context = {
            # JSON Mode 不会自动把 Schema 发给模型，因此显式提供
            "output_schema": (OutfitGenerationResult.model_json_schema()),
            "user_request": _get_latest_text(
                state,
                HumanMessage,
            ),
            "assistant_response": _get_latest_text(
                state,
                AIMessage,
            ),
            "requirement_analysis": (decoded_requirements[0] if decoded_requirements else None),
            "effective_style_constraints": (
                decoded_style_constraints[0] if decoded_style_constraints else None
            ),
            "knowledge_context": context_package.combined_content_for(
                ContextSource.KNOWLEDGE,
            ),
            "outfit_feedback_context": context_package.combined_content_for(
                ContextSource.OUTFIT_FEEDBACK,
            ),
            "recent_outfits_context": context_package.combined_content_for(
                ContextSource.RECENT_OUTFITS,
            ),
            "previous_outfit": (decoded_previous_outfit[0] if decoded_previous_outfit else None),
            "provided_weather": (decoded_weather[0] if decoded_weather else None),
            "weather_tool_results": decoded_weather_tool_results,
            "weather_outfit_guidance": (decoded_guidance[0] if decoded_guidance else ()),
            "style_profile_context": context_package.combined_content_for(
                ContextSource.STYLE_PROFILE,
            ),
            "wardrobe_items": _decode_context_values(
                context_package,
                ContextSource.WARDROBE,
            ),
            "products": _decode_context_values(
                context_package,
                ContextSource.PRODUCTS,
            ),
        }

        try:
            raw_result = structured_model.invoke(
                [
                    SystemMessage(
                        content=OUTFIT_GENERATION_SYSTEM_PROMPT,
                    ),
                    HumanMessage(
                        content=json.dumps(
                            generation_context,
                            ensure_ascii=False,
                        ),
                    ),
                ],
            )

            structured_result = OutfitGenerationResult.model_validate(
                raw_result,
            )
            recommendation = structured_result.outfit

            # 模型判断本轮不需要完整穿搭时，合法返回空结果
            if recommendation is None:
                return {
                    "outfit_recommendation": None,
                }

        # 模型供应商和解析器可能抛出不同异常，节点边界统一安全降级
        except Exception as exc:  # noqa: BLE001
            # 结构化输出失败时保留已经生成的文本回复，不暴露不可信 Outfit
            logger.warning(
                "结构化 Outfit 生成失败，已降级为文本回复：%s：%s",
                type(exc).__name__,
                exc,
            )
            return {
                "outfit_recommendation": None,
            }

        return {
            "outfit_recommendation": recommendation,
        }

    return generate_outfit
