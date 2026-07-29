from unittest.mock import Mock, patch

from app.core.config import Settings
from app.rag.vectorstores.provider import (
    get_knowledge_vector_store,
)


def test_get_knowledge_vector_store_builds_and_caches_store() -> None:
    """验证知识向量库的装配和缓存。"""

    # 清除其他调用可能留下的缓存
    get_knowledge_vector_store.cache_clear()

    # 创建独立测试配置
    settings = Settings(
        _env_file=None,
        embedding_model="test-embedding-model",
        embedding_device="cpu",
        chroma_persist_directory="./test-chroma",
        chroma_collection_name="test_collection",
    )

    # 创建假的 Embedding 和 Chroma 对象
    fake_embeddings = Mock()
    fake_vector_store = Mock()

    # 替换配置、Embedding 和 Chroma 工厂
    with (
        patch(
            "app.rag.vectorstores.provider.get_settings",
            return_value=settings,
        ) as mocked_get_settings,
        patch(
            "app.rag.vectorstores.provider.create_huggingface_embeddings",
            return_value=fake_embeddings,
        ) as mocked_create_embeddings,
        patch(
            "app.rag.vectorstores.provider.create_chroma_vector_store",
            return_value=fake_vector_store,
        ) as mocked_create_vector_store,
    ):
        # 第一次调用执行完整装配
        first_store = get_knowledge_vector_store()

        # 第二次调用应该直接读取缓存
        second_store = get_knowledge_vector_store()

    # 两次调用应返回同一个向量库
    assert first_store is fake_vector_store
    assert second_store is fake_vector_store

    # 每个工厂只应该执行一次
    mocked_get_settings.assert_called_once_with()
    mocked_create_embeddings.assert_called_once_with(settings)
    mocked_create_vector_store.assert_called_once_with(
        embeddings=fake_embeddings,
        collection_name="test_collection",
        persist_directory="./test-chroma",
    )

    # 测试结束后清除缓存，避免影响其他测试
    get_knowledge_vector_store.cache_clear()