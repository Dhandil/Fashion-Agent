"""每轮对话开始前的状态准备节点。"""

from collections.abc import Callable

from app.agents.state.shopping import ShoppingAgentState
from app.domain.entities.outfit import (
    OutfitRecommendation,
)


def create_prepare_turn_node() -> Callable[
    [ShoppingAgentState],
    dict[str, OutfitRecommendation | None],
]:
    """创建清理本轮输出并保留最近推荐的节点。"""

    def prepare_turn(
        state: ShoppingAgentState,
    ) -> dict[str, OutfitRecommendation | None]:
        """把上一轮 Outfit 保存为调整基线，再清空本轮输出。"""

        updates: dict[
            str,
            OutfitRecommendation | None,
        ] = {
            # 防止普通知识问答返回上一轮的旧结构化推荐
            "outfit_recommendation": None,
        }
        current_recommendation = state.get(
            "outfit_recommendation",
        )

        if current_recommendation is not None:
            updates[
                "previous_outfit_recommendation"
            ] = current_recommendation

        return updates

    return prepare_turn
