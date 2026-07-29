from langchain_core.vectorstores import (
    VectorStore,
    VectorStoreRetriever,
)


def create_knowledge_retriever(
    vector_store: VectorStore,
    top_k: int = 3,
) -> VectorStoreRetriever:
    """创建服装知识检索器。"""

    return vector_store.as_retriever(
        search_kwargs={
            "k": top_k,
        },
    )