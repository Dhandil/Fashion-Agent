"""每轮对话开始前的状态准备节点。"""

from collections.abc import Callable

from app.agents.state.serialization import coerce_model
from app.agents.state.shopping import ShoppingAgentState
from app.domain.entities.outfit import OutfitRecommendation
from app.memory.short_term.conversation_summary import ConversationSummary


def create_prepare_turn_node() -> Callable[
    [ShoppingAgentState],
    dict[str, object],
]:
    """创建清理本轮输出并保留最近推荐的节点。"""

    def prepare_turn(
        state: ShoppingAgentState,
    ) -> dict[str, object]:
        """把上一轮 Outfit 保存为调整基线，再清空本轮输出。"""

        updates: dict[str, object] = {
            # 防止普通知识问答返回上一轮的旧结构化推荐
            "outfit_recommendation": None,
            "outfit_gap_report": None,
            "outfit_feasibility_report": None,
            "outfit_correction_attempts": 0,
            "tool_policy_rejection_count": 0,
            # 以下字段都属于本轮派生上下文；路由跳过加载节点时必须清空旧值
            "knowledge_context": "",
            "knowledge_sources": [],
            "knowledge_provenance": [],
            "style_profile_context": "",
            "style_profile_snapshot": None,
            "outfit_feedback_context": "",
            "recent_outfits_context": "",
        }
        current_recommendation = coerce_model(
            state.get("outfit_recommendation"),
            OutfitRecommendation,
        )

        if current_recommendation is not None:
            updates["previous_outfit_recommendation"] = current_recommendation
        elif (
            state.get("previous_outfit_recommendation") is not None
            and not isinstance(
                state["previous_outfit_recommendation"],
                OutfitRecommendation,
            )
        ):
            # Redis 可能恢复普通字典；显式转换后供后续节点安全使用。
            updates["previous_outfit_recommendation"] = coerce_model(
                state["previous_outfit_recommendation"],
                OutfitRecommendation,
            )

        existing_summary = state.get("conversation_summary")
        if existing_summary is not None and not isinstance(
            existing_summary,
            ConversationSummary,
        ):
            # Redis 可能将摘要恢复为字典；无效摘要直接清除。
            updates["conversation_summary"] = coerce_model(
                existing_summary,
                ConversationSummary,
            )

        return updates

    return prepare_turn
