from collections.abc import Callable

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AnyMessage

from app.agents.state.shopping import ShoppingAgentState


def create_chat_node(
        model: BaseChatModel,
) -> Callable[[ShoppingAgentState], dict[str, list[AnyMessage]]]:
    """创建一个使用指定模型的聊天节点。"""

    def chat_node(
            state: ShoppingAgentState,
    ) -> dict[str, list[AnyMessage]]:
        """读取对话状态并调用聊天模型。"""

        # 将完整对话历史发送给聊天模型
        response = model.invoke(state["messages"])

        # 返回的新消息会由 add_messages 追加到 State
        return {"messages": [response]}

    return chat_node