from pathlib import Path

from app.core.config import get_settings
from app.rag.ingestion import index_markdown_directory
from app.rag.loaders.text_splitter import create_text_splitter
from app.rag.vectorstores.provider import (
    get_knowledge_vector_store,
)


def main() -> None:
    """将示例服装知识索引到持久化 Chroma。"""

    # 读取 RAG 配置
    settings = get_settings()

    # 创建配置化的文本切分器
    text_splitter = create_text_splitter(
        chunk_size=settings.rag_chunk_size,
        chunk_overlap=settings.rag_chunk_overlap,
    )

    # 获取带有 BGE 和持久化目录的 Chroma
    vector_store = get_knowledge_vector_store()

    # 当前先索引可提交的示例知识目录
    knowledge_directory = Path("data/samples")


    # 执行加载、切分、向量化和写入
    indexed_count = index_markdown_directory(
        directory=knowledge_directory,
        text_splitter=text_splitter,
        vector_store=vector_store,
    )

    print(f"知识入库完成，共索引 {indexed_count} 个片段。")


if __name__ == "__main__":
    main()