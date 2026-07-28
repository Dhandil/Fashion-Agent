from unittest.mock import Mock

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage

from app.agents.graphs.shopping import create_shopping_graph


def test_shopping_graph_runs_chat_node() -> None:
    """验证购物工作流能够执行聊天节点并合并消息。"""

    # 创建假模型，避免调用真实 LLM
    model = Mock(spec=BaseChatModel)
    model.invoke.return_value = AIMessage(
        content="请告诉我你的预算",
    )

    # 创建并编译工作流
    graph = create_shopping_graph(model)

    # 使用用户消息作为工作流的初始状态
    result = graph.invoke(
        {
            "messages": [
                HumanMessage(content="我想买一件衬衫")
            ],
        }
    )

    # 验证图执行过程中调用了一次模型
    assert model.invoke.call_count == 1

    # add_messages 应该八六用户消息并追加 AI 回复
    assert len(result["messages"]) == 2
    assert result["messages"][0].content == "我想买一件衬衫"
    assert result["messages"][1].content == "请告诉我你的预算"