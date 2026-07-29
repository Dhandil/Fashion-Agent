"""Agent 工具调用路由。"""

from langchain_core.messages import AIMessage
from langgraph.graph import END

from app.agents.state.shopping import ShoppingAgentState


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
    if (
        isinstance(last_message, AIMessage)
        and last_message.tool_calls
    ):
        return "tools"

    # 模型没有发起工具调用时，当前工作流结束
    return END