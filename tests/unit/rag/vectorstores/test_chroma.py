from unittest.mock import Mock, patch

from langchain_core.embeddings import Embeddings

from app.rag.vectorstores.chroma import create_chroma_vector_store


def test_create_chroma_vector_store_uses_parameters() -> None:
    """验证 Chroma 工厂正确传递创建参数。"""

    # 创建符合 Embeddings 接口的假对象
    embeddings = Mock(spec=Embeddings)

    # 替换真实 Chroma，避免创建数据库
    with patch(
        "app.rag.vectorstores.chroma.Chroma",
    ) as mocked_chroma:
        vector_store = create_chroma_vector_store(
            embeddings=embeddings,
            collection_name="test_collection",
            persist_directory=None,
        )

    # 工厂应该返回 Chroma 创建出的对象
    assert vector_store is mocked_chroma.return_value

    # 验证所有参数都正确传入
    mocked_chroma.assert_called_once_with(
        collection_name="test_collection",
        embedding_function=embeddings,
        persist_directory=None,
    )