"""拒绝不符合当前结构化需求权限的工具调用。"""

from langchain_core.messages import AIMessage, ToolMessage

from app.agents.routing.tools import (
    get_disallowed_tool_calls,
)
from app.agents.state.shopping import ShoppingAgentState


def reject_disallowed_tool_calls(
    state: ShoppingAgentState,
) -> dict[str, list[ToolMessage] | int]:
    """用 ToolMessage 解释拒绝原因，让模型转为安全文本回复。"""

    last_message = state["messages"][-1]
    if not isinstance(last_message, AIMessage):
        return {
            "messages": [],
            "tool_policy_rejection_count": state.get(
                "tool_policy_rejection_count",
                0,
            ),
        }

    disallowed_names = {tool_call["name"] for tool_call in get_disallowed_tool_calls(state)}
    tool_messages = [
        ToolMessage(
            name=tool_call["name"],
            tool_call_id=tool_call["id"],
            status="error",
            content=(
                "本轮结构化需求不允许调用该工具。"
                "请不要继续调用工具，改为提出必要问题或说明能力边界。"
                if tool_call["name"] in disallowed_names
                else ("本轮包含不允许的混合工具调用，所有调用均已取消；请根据需求权限重新回答。")
            ),
        )
        for tool_call in last_message.tool_calls
    ]
    return {
        "messages": tool_messages,
        "tool_policy_rejection_count": (state.get("tool_policy_rejection_count", 0) + 1),
    }
