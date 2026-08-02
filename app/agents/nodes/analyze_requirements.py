"""当前轮穿搭需求的结构化分析节点。"""

import json
import logging
from collections.abc import Callable

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
)

from app.agents.context import get_current_turn_messages
from app.agents.prompts.requirements import (
    REQUIREMENT_ANALYSIS_SYSTEM_PROMPT,
)
from app.agents.schemas.requirements import (
    OutfitRequirementAnalysis,
    RequestIntent,
    RequirementField,
    ShoppingIntent,
)
from app.agents.state.shopping import ShoppingAgentState
from app.core.observability import (
    log_event,
    observe_operation,
)

logger = logging.getLogger(__name__)

_SHOPPING_TERMS = (
    "购买",
    "买一",
    "买件",
    "买双",
    "商品",
    "价格",
    "多少钱",
    "链接",
    "选购",
    "比价",
    "帮我找",
    "找一件",
    "推荐商品",
    "店铺",
    "平台",
)
_SHOPPING_NEGATIONS = (
    "不买",
    "不想买",
    "不要买",
    "无需购买",
    "不需要购买",
    "不查商品",
    "不用查商品",
    "不要查商品",
    "无需查商品",
    "不需要查商品",
    "别查商品",
)
_WARDROBE_TERMS = (
    "衣橱",
    "衣柜",
    "已有衣物",
    "现有衣物",
    "我的衣服",
    "我已有",
)
_OUTFIT_SCENARIO_TERMS = (
    "通勤",
    "上班",
    "工作",
    "面试",
    "见客户",
    "约会",
    "聚会",
    "婚礼",
    "旅行",
    "运动",
    "健身",
    "户外",
    "逛街",
    "咖啡馆",
    "周末",
    "日常",
    "上课",
    "校园",
)
_OUTFIT_REQUEST_TERMS = (
    "搭配",
    "穿搭",
    "怎么穿",
    "服装建议",
)


def _latest_user_text(state: ShoppingAgentState) -> str:
    """读取当前轮最后一条用户文本。"""

    for message in reversed(
        get_current_turn_messages(state["messages"]),
    ):
        if isinstance(message, HumanMessage) and isinstance(message.content, str):
            return message.content
    return ""


def _has_explicit_shopping_intent(text: str) -> bool:
    """用确定性词面规则确认模型不能自行扩大购物权限。"""

    return not any(negation in text for negation in _SHOPPING_NEGATIONS) and any(
        term in text for term in _SHOPPING_TERMS
    )


def _has_explicit_wardrobe_intent(text: str) -> bool:
    """识别用户明确要求读取已有衣物的表达。"""

    return any(term in text for term in _WARDROBE_TERMS)


def _has_outfit_scenario_signal(text: str) -> bool:
    """识别足以支持第一版搭配的明确使用情境。"""

    return any(term in text for term in _OUTFIT_SCENARIO_TERMS)


def _has_outfit_request_signal(text: str) -> bool:
    """识别用户正在请求穿搭方案而非商品购买。"""

    return _has_outfit_scenario_signal(text) or any(
        term in text for term in _OUTFIT_REQUEST_TERMS
    )


def _is_currently_mentioned(
    value: str,
    current_request: str,
) -> bool:
    """判断模型提取值是否确实出现在当前用户文本中。"""

    normalised_value = "".join(value.casefold().split())
    normalised_request = "".join(
        current_request.casefold().split(),
    )
    aliases = {
        normalised_value,
        normalised_value.removesuffix("风格"),
        normalised_value.removesuffix("材质"),
        normalised_value.removesuffix("颜色"),
    }
    return any(alias and alias in normalised_request for alias in aliases)


def _fallback_analysis(
    current_request: str,
) -> OutfitRequirementAnalysis:
    """结构化模型不可用时提供不阻断旧链路的保守分析。"""

    shopping_is_explicit = _has_explicit_shopping_intent(
        current_request,
    )
    wardrobe_is_explicit = _has_explicit_wardrobe_intent(
        current_request,
    )
    outfit_is_explicit = _has_outfit_request_signal(
        current_request,
    )
    return OutfitRequirementAnalysis(
        intent=(
            RequestIntent.SHOPPING
            if shopping_is_explicit
            else (
                RequestIntent.OUTFIT
                if outfit_is_explicit
                else RequestIntent.OTHER
            )
        ),
        wardrobe_preferred=wardrobe_is_explicit,
        needs_wardrobe=wardrobe_is_explicit,
        shopping_intent=(ShoppingIntent.EXPLICIT if shopping_is_explicit else ShoppingIntent.NONE),
        # 降级时不凭规则阻断请求，由现有 Chat 节点继续回答。
        is_sufficient=True,
    )


def _apply_deterministic_permissions(
    analysis: OutfitRequirementAnalysis,
    current_request: str,
) -> OutfitRequirementAnalysis:
    """以用户原文的确定性信号收紧购物和衣橱工具权限。"""

    explicit_shopping = _has_explicit_shopping_intent(
        current_request,
    )
    explicit_wardrobe = _has_explicit_wardrobe_intent(
        current_request,
    )
    wardrobe_required = (
        explicit_wardrobe
        or analysis.intent is RequestIntent.OUTFIT_ADJUSTMENT
    )
    resolved_intent = analysis.intent
    if (
        resolved_intent is RequestIntent.SHOPPING
        and not explicit_shopping
    ):
        resolved_intent = (
            RequestIntent.OUTFIT
            if _has_outfit_request_signal(current_request)
            else RequestIntent.OTHER
        )
    updates: dict[str, object] = {
        "intent": resolved_intent,
        "shopping_intent": (ShoppingIntent.EXPLICIT if explicit_shopping else ShoppingIntent.NONE),
        "needs_wardrobe": wardrobe_required,
        "wardrobe_preferred": wardrobe_required,
    }

    # 避免项必须能在当前用户文本中核对，不能从摘要或历史消息复制。
    current_avoided_styles = tuple(
        value
        for value in analysis.avoided_styles
        if _is_currently_mentioned(
            value,
            current_request,
        )
    )
    current_avoided_colors = tuple(
        value
        for value in analysis.avoided_colors
        if _is_currently_mentioned(
            value,
            current_request,
        )
    )
    current_avoided_materials = tuple(
        value
        for value in analysis.avoided_materials
        if _is_currently_mentioned(
            value,
            current_request,
        )
    )

    # 当前轮明确避免项优先于同一轮喜欢项，避免模型输出自相矛盾。
    avoided_style_keys = {value.casefold() for value in current_avoided_styles}
    avoided_color_keys = {value.casefold() for value in current_avoided_colors}
    updates.update(
        {
            "avoided_styles": current_avoided_styles,
            "avoided_colors": current_avoided_colors,
            "avoided_materials": current_avoided_materials,
            "style_preferences": tuple(
                value
                for value in analysis.style_preferences
                if value.casefold() not in avoided_style_keys
            ),
            "color_preferences": tuple(
                value
                for value in analysis.color_preferences
                if value.casefold() not in avoided_color_keys
            ),
        },
    )

    # 地点和日期已齐全时，实时天气应由工具查询，不应继续追问用户提供 weather。
    if (
        analysis.needs_weather
        and analysis.location
        and analysis.target_date
        and RequirementField.WEATHER in analysis.missing_fields
    ):
        remaining_missing_fields = tuple(
            field
            for field in analysis.missing_fields
            if field is not RequirementField.WEATHER
        )
        updates.update(
            {
                "is_sufficient": (
                    not remaining_missing_fields
                ),
                "missing_fields": remaining_missing_fields,
            },
        )

    # 全新完整穿搭如果连使用场景都没有，无法判断正式度和功能需求。
    # 局部调整可以沿用 previous_outfit，因此不应用这条规则。
    if analysis.intent is RequestIntent.OUTFIT:
        has_scenario_signal = bool(
            analysis.scenario,
        ) or _has_outfit_scenario_signal(current_request)
        if not has_scenario_signal:
            missing_fields = tuple(
                dict.fromkeys(
                    (
                        RequirementField.SCENARIO,
                        *analysis.missing_fields,
                    ),
                ),
            )[:3]
            updates.update(
                {
                    "is_sufficient": False,
                    "missing_fields": missing_fields,
                },
            )
        elif (
            not analysis.is_sufficient
            and analysis.missing_fields
            and set(analysis.missing_fields) == {RequirementField.SCENARIO}
        ):
            # 模型可能把“周末”等情境放进日期字段，同时又错误要求补场景。
            # 只有唯一缺失项就是场景时才恢复为充分，避免掩盖地点等真实缺口。
            updates.update(
                {
                    "is_sufficient": True,
                    "missing_fields": (),
                },
            )

    return analysis.model_copy(update=updates)


def _recent_conversation_text(
    state: ShoppingAgentState,
    max_chars: int = 4_000,
) -> list[dict[str, str]]:
    """提供有限的近期人机文本，排除 ToolMessage 和大块工具结果。"""

    summary = state.get("conversation_summary")
    covered_message_count = (
        summary.covered_message_count
        if summary is not None and summary.covered_message_count <= len(state["messages"])
        else 0
    )
    recent_messages = state["messages"][covered_message_count:]
    records: list[dict[str, str]] = []
    used_chars = 0
    for message in reversed(recent_messages):
        if not isinstance(message, HumanMessage | AIMessage):
            continue
        if not isinstance(message.content, str):
            continue
        remaining = max_chars - used_chars
        if remaining <= 0:
            break
        content = message.content[:remaining]
        records.append(
            {
                "role": ("user" if isinstance(message, HumanMessage) else "assistant"),
                "content": content,
            },
        )
        used_chars += len(content)

    records.reverse()
    return records


def create_requirement_analysis_node(
    model: BaseChatModel,
) -> Callable[
    [ShoppingAgentState],
    dict[str, OutfitRequirementAnalysis],
]:
    """创建已绑定结构化输出模型的需求分析节点。"""

    structured_model = model.with_structured_output(
        OutfitRequirementAnalysis,
        method="json_mode",
    )

    def analyze_requirements(
        state: ShoppingAgentState,
    ) -> dict[str, OutfitRequirementAnalysis]:
        """分析当前请求，并在失败时安全降级到保守规则。"""

        current_request = _latest_user_text(state)
        conversation_summary = state.get(
            "conversation_summary",
        )
        payload = {
            "output_schema": (OutfitRequirementAnalysis.model_json_schema()),
            "current_request": current_request,
            "recent_conversation": _recent_conversation_text(
                state,
            ),
            "conversation_summary": (
                conversation_summary.content if conversation_summary is not None else ""
            ),
        }

        try:
            with observe_operation(
                logger,
                "agent.llm",
                purpose="requirement_analysis",
            ):
                raw_analysis = structured_model.invoke(
                    [
                        SystemMessage(
                            content=(REQUIREMENT_ANALYSIS_SYSTEM_PROMPT),
                        ),
                        HumanMessage(
                            content=json.dumps(
                                payload,
                                ensure_ascii=False,
                            ),
                        ),
                    ],
                )
            analysis = OutfitRequirementAnalysis.model_validate(
                raw_analysis,
            )
            analysis = _apply_deterministic_permissions(
                analysis,
                current_request,
            )
            degraded = False
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "需求结构化分析失败，已使用保守规则降级：%s",
                type(exc).__name__,
            )
            analysis = _fallback_analysis(current_request)
            degraded = True

        log_event(
            logger,
            "agent.requirements.analyzed",
            intent=analysis.intent.value,
            is_sufficient=analysis.is_sufficient,
            missing_field_count=len(
                analysis.missing_fields,
            ),
            needs_wardrobe=analysis.needs_wardrobe,
            needs_weather=analysis.needs_weather,
            shopping_intent=analysis.shopping_intent.value,
            degraded=degraded,
        )
        return {
            "requirement_analysis": analysis,
        }

    return analyze_requirements
