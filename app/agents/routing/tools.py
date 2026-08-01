"""Agent 工具调用路由。"""

from langchain_core.messages import (
    AIMessage,
    ToolCall,
    ToolMessage,
)
from langgraph.graph import END

from app.agents.context import get_current_turn_messages
from app.agents.schemas.requirements import (
    OutfitRequirementAnalysis,
    ShoppingIntent,
)
from app.agents.state.shopping import ShoppingAgentState


def is_tool_call_allowed(
    tool_name: str,
    analysis: OutfitRequirementAnalysis | None,
) -> bool:
    """根据结构化需求决定内置动态数据工具是否可执行。"""

    if analysis is None:
        return True
    if not analysis.is_sufficient:
        return False
    if tool_name == "search_products":
        return analysis.shopping_intent is ShoppingIntent.EXPLICIT
    if tool_name == "search_wardrobe":
        return analysis.needs_wardrobe
    if tool_name == "get_weather":
        return analysis.needs_weather

    # 未知扩展工具仍由其自身权限和后续 Registry 策略负责。
    return True


def get_disallowed_tool_calls(
    state: ShoppingAgentState,
) -> tuple[ToolCall, ...]:
    """返回当前模型回复中不符合需求权限的工具调用。"""

    if not state["messages"]:
        return ()
    last_message = state["messages"][-1]
    if not isinstance(last_message, AIMessage):
        return ()

    analysis = state.get("requirement_analysis")
    return tuple(
        tool_call
        for tool_call in last_message.tool_calls
        if not is_tool_call_allowed(
            tool_call["name"],
            analysis,
        )
    )


def route_after_chat(state: ShoppingAgentState) -> str:
    """根据模型回复判断下一步执行工具还是结束流程。"""

    # 获取当前对话状态中的全部消息
    messages = state["messages"]

    # 防御性判断：没有消息时无法执行工具，直接结束
    if not messages:
        return END

    # 最后一条消息是聊天模型刚刚生成的回复
    last_message = messages[-1]

    # AIMessage 的 tool_calls 保存模型请求调用的工具
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        if get_disallowed_tool_calls(state):
            if (
                state.get(
                    "tool_policy_rejection_count",
                    0,
                )
                >= 1
            ):
                return END
            return "reject_tools"
        return "tools"

    # 当前轮查询过衣橱时，再判断是否应该生成结构化 Outfit
    current_turn_messages = get_current_turn_messages(
        messages,
    )

    if any(
        isinstance(message, ToolMessage)
        and message.name == "search_wardrobe"
        and message.status == "success"
        for message in current_turn_messages
    ):
        return "generate_outfit"

    # 模型没有发起工具调用时，当前工作流结束
    return END
