from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph.message import add_messages


def test_add_message_preserves_conversation_history() -> None:
    """验证新消息会追加到已有对话历史。"""

    # 模拟已有的用户消息
    current_messages = [
        HumanMessage(content="我想买一件衬衫"),
    ]

    # 模拟 Agent 节点产生的新回复
    new_messages = [
        AIMessage(content="请告诉我你的预算"),
    ]

    # 使用与 ShoppingAgentState 相同的消息合并规则
    merged_messages = add_messages(
        current_messages,
        new_messages,
    )

    # 合并后应该同时保留用户消息和 AI 消息
    assert len(merged_messages) == 2
    assert merged_messages[0].content == "我想买一件衬衫"
    assert merged_messages[1].content == "请告诉我你的预算"