from functools import lru_cache

from langchain_core.retrievers import BaseRetriever

from app.core.config import get_settings
from app.rag.retrievers.knowledge import (
    create_knowledge_retriever,
)
from app.rag.vectorstores.provider import (
    get_knowledge_vector_store,
)


@lru_cache
def get_knowledge_retriever() -> BaseRetriever:
    """创建并缓存服装知识检索器。"""

    # 读取检索数量配置
    settings = get_settings()

    # 创建持久化服装知识向量库
    vector_store = get_knowledge_vector_store()

    # 创建标准 LangChain Retriever
    return create_knowledge_retriever(
        vector_store=vector_store,
        top_k=settings.rag_top_k,
        candidate_k=settings.rag_candidate_k,
    )
