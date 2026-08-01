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
    ShoppingIntent,
)
from app.agents.state.shopping import ShoppingAgentState
from app.core.observability import log_event

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
)
_WARDROBE_TERMS = (
    "衣橱",
    "衣柜",
    "已有衣物",
    "现有衣物",
    "我的衣服",
    "我已有",
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
    return OutfitRequirementAnalysis(
        intent=(RequestIntent.SHOPPING if shopping_is_explicit else RequestIntent.OTHER),
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
    return analysis.model_copy(
        update={
            "shopping_intent": (
                ShoppingIntent.EXPLICIT if explicit_shopping else ShoppingIntent.NONE
            ),
            "needs_wardrobe": (analysis.needs_wardrobe or explicit_wardrobe),
            "wardrobe_preferred": (analysis.wardrobe_preferred or explicit_wardrobe),
        },
    )


def _recent_conversation_text(
    state: ShoppingAgentState,
    max_chars: int = 4_000,
) -> list[dict[str, str]]:
    """提供有限的近期人机文本，排除 ToolMessage 和大块工具结果。"""

    records: list[dict[str, str]] = []
    used_chars = 0
    for message in reversed(state["messages"]):
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
        payload = {
            "output_schema": (OutfitRequirementAnalysis.model_json_schema()),
            "current_request": current_request,
            "recent_conversation": _recent_conversation_text(
                state,
            ),
        }

        try:
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
