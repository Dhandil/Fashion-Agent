from langchain_chroma import Chroma
from langchain_core.embeddings import Embeddings


def create_chroma_vector_store(
    embeddings: Embeddings,
    collection_name: str = "fashion_knowledge",
    persist_directory: str |None = None,
) -> Chroma:
    """创建 Chroma 向量存储。"""

    return Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=persist_directory,
    )