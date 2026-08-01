"""每轮对话开始前的状态准备节点。"""

from collections.abc import Callable

from app.agents.state.shopping import ShoppingAgentState


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
            "outfit_feasibility_report": None,
            "outfit_correction_attempts": 0,
            "tool_policy_rejection_count": 0,
            # 以下字段都属于本轮派生上下文；路由跳过加载节点时必须清空旧值
            "knowledge_context": "",
            "knowledge_sources": [],
            "style_profile_context": "",
            "outfit_feedback_context": "",
            "recent_outfits_context": "",
        }
        current_recommendation = state.get(
            "outfit_recommendation",
        )

        if current_recommendation is not None:
            updates["previous_outfit_recommendation"] = current_recommendation

        return updates

    return prepare_turn
