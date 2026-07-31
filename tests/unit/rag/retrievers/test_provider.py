from unittest.mock import Mock, patch

from app.core.config import Settings
from app.rag.retrievers.provider import (
    get_knowledge_retriever,
)


def test_get_knowledge_retriever_builds_and_caches_retriever() -> None:
    """验证知识 Retriever 的装配和缓存。"""

    # 清除其他调用可能留下的缓存
    get_knowledge_retriever.cache_clear()

    # 创建测试配置
    settings = Settings(
        _env_file=None,
        rag_top_k=5,
        rag_candidate_k=30,
    )

    # 创建假的 Vector Store 和 Retriever
    fake_vector_store = Mock()
    fake_retriever = Mock()

    # 替换配置、Vector Store Provider 和 Retriever 工厂
    with (
        patch(
            "app.rag.retrievers.provider.get_settings",
            return_value=settings,
        ) as mocked_get_settings,
        patch(
            "app.rag.retrievers.provider.get_knowledge_vector_store",
            return_value=fake_vector_store,
        ) as mocked_get_vector_store,
        patch(
            "app.rag.retrievers.provider.create_knowledge_retriever",
            return_value=fake_retriever,
        ) as mocked_create_retriever,
    ):
        # 第一次调用执行完整装配
        first_retriever = get_knowledge_retriever()

        # 第二次调用应该直接使用缓存
        second_retriever = get_knowledge_retriever()

    # 两次调用都应返回同一个 Retriever
    assert first_retriever is fake_retriever
    assert second_retriever is fake_retriever

    # 所有装配函数都只应该调用一次
    mocked_get_settings.assert_called_once_with()
    mocked_get_vector_store.assert_called_once_with()
    mocked_create_retriever.assert_called_once_with(
        vector_store=fake_vector_store,
        top_k=5,
        candidate_k=30,
    )

    # 清除测试产生的缓存
    get_knowledge_retriever.cache_clear()
