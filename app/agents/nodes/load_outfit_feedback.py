"""加载用户 Outfit 反馈的个性化上下文节点。"""

from collections.abc import Awaitable, Callable, Sequence

from app.agents.state.shopping import ShoppingAgentState
from app.domain.entities.outfit import Outfit
from app.domain.entities.outfit_feedback import (
    OutfitFeedback,
    OutfitFeedbackSentiment,
)
from app.domain.repositories.outfit import OutfitRepository
from app.domain.repositories.outfit_feedback import (
    OutfitFeedbackRepository,
)

DEFAULT_FEEDBACK_LIMIT = 20


def build_outfit_feedback_context(
    feedback_items: Sequence[OutfitFeedback],
    outfits: Sequence[Outfit],
) -> str:
    """把反馈和关联穿搭整理成模型可读的有限上下文。"""

    outfits_by_id = {
        outfit.outfit_id: outfit
        for outfit in outfits
    }
    context_records: list[str] = []

    for feedback in feedback_items:
        outfit = outfits_by_id.get(feedback.outfit_id)

        # 数据不完整时跳过记录，避免让模型猜测原穿搭内容
        if outfit is None:
            continue

        sentiment_label = {
            OutfitFeedbackSentiment.LIKE: "喜欢",
            OutfitFeedbackSentiment.DISLIKE: "不喜欢",
            None: "未选择态度",
        }[feedback.sentiment]
        style_tags = "、".join(outfit.style_tags) or "未标注"
        item_names = "、".join(
            item.name for item in outfit.items
        )
        comment = feedback.comment or "未填写说明"

        context_records.append(
            (
                f"- 历史穿搭：{outfit.name}；"
                f"场景：{outfit.scenario}；"
                f"风格：{style_tags}；"
                f"单品：{item_names}；"
                f"用户态度：{sentiment_label}；"
                f"用户说明：{comment}"
            ),
        )

    return "\n".join(context_records)


def create_load_outfit_feedback_node(
    outfit_repository: OutfitRepository,
    feedback_repository: OutfitFeedbackRepository,
    user_id: str,
    limit: int = DEFAULT_FEEDBACK_LIMIT,
) -> Callable[
    [ShoppingAgentState],
    Awaitable[dict[str, str]],
]:
    """创建绑定当前用户和请求级仓库的反馈加载节点。"""

    async def load_outfit_feedback(
        _state: ShoppingAgentState,
    ) -> dict[str, str]:
        """查询最近反馈，并与原穿搭合并成个性化上下文。"""

        feedback_items = await feedback_repository.search(
            user_id=user_id,
            limit=limit,
        )

        if not feedback_items:
            return {
                "outfit_feedback_context": "",
            }

        outfit_ids = tuple(
            feedback.outfit_id
            for feedback in feedback_items
        )
        outfits = await outfit_repository.get_by_ids(
            user_id=user_id,
            outfit_ids=outfit_ids,
        )

        return {
            "outfit_feedback_context": (
                build_outfit_feedback_context(
                    feedback_items=feedback_items,
                    outfits=outfits,
                )
            ),
        }

    return load_outfit_feedback
