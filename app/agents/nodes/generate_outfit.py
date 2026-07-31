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
from app.agents.prompts.outfit import (
    OUTFIT_GENERATION_SYSTEM_PROMPT,
)
from app.agents.schemas.outfit import (
    OutfitGenerationResult,
)
from app.agents.state.shopping import ShoppingAgentState
from app.domain.entities.outfit import (
    OutfitItemSource,
    OutfitRecommendation,
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
        if (
            isinstance(message, message_type)
            and isinstance(message.content, str)
        ):
            return message.content

    return ""


def _get_record_ids(
    records: tuple[dict[str, Any], ...],
    id_field: str,
) -> set[str]:
    """从工具记录中提取有效字符串 ID。"""

    return {
        record_id
        for record in records
        if isinstance(
            record_id := record.get(id_field),
            str,
        )
        and record_id
    }


def _validate_outfit_source_ids(
    recommendation: OutfitRecommendation,
    wardrobe_ids: set[str],
    product_ids: set[str],
) -> None:
    """验证 Outfit 引用的真实来源 ID 均来自本轮工具结果。"""

    for item in (
        *recommendation.items,
        *recommendation.alternatives,
    ):
        if (
            item.source is OutfitItemSource.WARDROBE
            and item.source_reference_id not in wardrobe_ids
        ):
            raise ValueError(
                "Outfit 引用了本轮衣橱结果中不存在的 ID",
            )

        if (
            item.source is OutfitItemSource.PRODUCT
            and item.source_reference_id not in product_ids
        ):
            raise ValueError(
                "Outfit 引用了本轮商品结果中不存在的 ID",
            )


def create_outfit_generation_node(
    model: BaseChatModel,
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

        wardrobe_records = get_current_turn_tool_records(
            state["messages"],
            "search_wardrobe",
        )
        product_records = get_current_turn_tool_records(
            state["messages"],
            "search_products",
        )

        generation_context = {
            # JSON Mode 不会自动把 Schema 发给模型，因此显式提供
            "output_schema": (
                OutfitGenerationResult.model_json_schema()
            ),
            "user_request": _get_latest_text(
                state,
                HumanMessage,
            ),
            "assistant_response": _get_latest_text(
                state,
                AIMessage,
            ),
            "knowledge_context": state.get(
                "knowledge_context",
                "",
            ),
            "outfit_feedback_context": state.get(
                "outfit_feedback_context",
                "",
            ),
            "style_profile_context": state.get(
                "style_profile_context",
                "",
            ),
            "wardrobe_items": wardrobe_records,
            "products": product_records,
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

            _validate_outfit_source_ids(
                recommendation=recommendation,
                wardrobe_ids=_get_record_ids(
                    wardrobe_records,
                    "wardrobe_item_id",
                ),
                product_ids=_get_record_ids(
                    product_records,
                    "product_id",
                ),
            )
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
