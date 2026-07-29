from functools import lru_cache

from langchain_chroma import Chroma

from app.core.config import get_settings
from app.rag.embeddings.huggingface import (
    create_huggingface_embeddings,
)
from app.rag.vectorstores.chroma import (
    create_chroma_vector_store,
)


@lru_cache
def get_knowledge_vector_store() -> Chroma:
    """创建并缓存服装知识向量库。"""

    # 读取 Chroma 和 Ebedding 配置
    settings = get_settings()

    # 创建本地中文 Embedding
    embeddings = create_huggingface_embeddings(settings)

    # 创建持久化 Chroma 集合
    return create_chroma_vector_store(
        embeddings=embeddings,
        collection_name=settings.chroma_collection_name,
        persist_directory=settings.chroma_persist_directory,
    )