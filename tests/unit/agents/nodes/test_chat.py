from unittest.mock import Mock

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage

from app.agents.nodes.chat import create_chat_node
from app.agents.state.shopping import ShoppingAgentState


def test_chat_node_invokes_bound_model() -> None:
    """验证聊天节点会调用闭包中绑定的模型。"""

    # 创建一个符合 BaseChatModel 接口的假模型
    model = Mock(spec=BaseChatModel)

    # 指定假模型被调用后返回的 AI 消息
    model.invoke.return_value = AIMessage(content="请告诉我你的预算")

    # 创建节点，model 会被保存在闭包中
    chat_node = create_chat_node(model)

    # 模拟 LangGraph 传入的当前状态
    state: ShoppingAgentState = {
        "messages": [
            HumanMessage(content="我想买一件衬衫"),
        ],
    }

    # 执行节点，此时闭包中的 model 才会被调用
    result = chat_node(state)

    # 验证模型接收到完整的历史消息
    model.invoke.assert_called_once_with(state["messages"])

    # 验证节点返回模型产生的新消息
    assert len(result["messages"]) == 1
    assert result["messages"][0].content == "请告诉我你的预算"