from unittest.mock import Mock

from langchain_core.vectorstores import VectorStore

from app.rag.retrievers.knowledge import (
    create_knowledge_retriever,
)


def test_create_knowledge_retriever_uses_top_k() -> None:
    """验证 Retriever 正确使用检索数量配置。"""

    # 创建假的 Vector Store 和 Retriever
    vector_store = Mock(spec=VectorStore)
    fake_retriever = Mock()

    # 指定 as_retriever() 返回的对象
    vector_store.as_retriever.return_value = fake_retriever

    # 创建检索器
    retriever = create_knowledge_retriever(
        vector_store=vector_store,
        top_k=5,
    )

    # 工厂应返回 Vector Store 创建出的 Retriever
    assert retriever is fake_retriever

    # 验证 top_k 被转换成底层检索参数 k
    vector_store.as_retriever.assert_called_once_with(
        search_kwargs={
            "k": 5,
        },
    )