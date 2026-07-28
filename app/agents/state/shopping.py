from typing import TypedDict, Annotated

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class ShoppingAgentState(TypedDict):
    """购物 Agent 在工作流中共享的状态。"""

    # 保存用户、AI 和工具产生的消息
    # add_messages 负责把新消息追加到现有的消息列表
    messages: Annotated[list[AnyMessage], add_messages]