from unittest.mock import Mock

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage
from langchain_core.retrievers import BaseRetriever

from app.agents.nodes.retrieve_knowledge import (
    create_retrieve_knowledge_node,
)
from app.agents.state.shopping import ShoppingAgentState


def test_retrieve_knowledge_node_builds_context() -> None:
    """验证 RAG Node 检索并组合知识上下文。"""

    # 创建假的 Retriever
    retriever = Mock(spec=BaseRetriever)

    # 模拟 Retriever 返回两个知识片段
    retriever.invoke.return_value = [
        Document(
            page_content="亚麻面料透气，适合夏季。",
            metadata={
                "source": "data/samples/fabrics.md",
            },
        ),
        Document(
            page_content="棉质面料柔软，适合日常穿着。",
            metadata={
                "source": "data/samples/fabrics.md",
            },
        ),
    ]

    # 创建已经绑定 Retriever 的节点
    retrieve_knowledge = create_retrieve_knowledge_node(
        retriever,
    )

    # 模拟包含用户问题的 Agent State
    state: ShoppingAgentState = {
        "messages": [
            HumanMessage(
                content="夏天通勤适合什么面料？",
            ),
        ],
    }

    # 执行 RAG Node
    result = retrieve_knowledge(state)

    # Retriever 应收到用户最新问题
    retriever.invoke.assert_called_once_with(
        "夏天通勤适合什么面料？",
    )

    # 两个片段应该用空行连接
    assert result == {
        "knowledge_context": (
            "亚麻面料透气，适合夏季。\n\n"
            "棉质面料柔软，适合日常穿着。"
        ),
        "knowledge_sources": [
            "data/samples/fabrics.md",
        ],
    }