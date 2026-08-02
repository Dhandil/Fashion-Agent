from hashlib import sha256
from pathlib import Path

from langchain_core.vectorstores import VectorStore
from langchain_text_splitters.base import TextSplitter

from app.rag.loaders.markdown import load_markdown_documents


def _create_chunk_id(
    document_content: str,
    source: str,
) -> str:
    """根据片段内容和来源生成稳定 ID。"""

    # 将来源和正文组合，避免不同文件的相同文字使用同一个 ID
    identity = f"{source}\n{document_content}"

    # SHA-256 将文本转换成固定长度的十六进制标识
    return sha256(identity.encode("utf-8")).hexdigest()

def index_markdown_directory(
    directory: Path,
    text_splitter: TextSplitter,
    vector_store: VectorStore,
) -> int:
    """加载、切分并索引目录中的 Markdown 文档。"""

    # 从目录中加载非空 Markdown 文档
    documents = load_markdown_documents(directory)

    # 将长文档切分成适合检索的小片段
    chunks = text_splitter.split_documents(documents)

    # 没有有效片段时不调用向量数据库
    if not chunks:
        return 0

    # 为每个片段生成稳定 ID， 避免重复执行时产生重复记录
    chunk_ids = [
        _create_chunk_id(
            document_content=chunk.page_content,
            source=str(chunk.metadata.get("source", "")),
        )
        for chunk in chunks
    ]

    # Chroma 会通过自己的 Embedding Function 为片段生成向量
    vector_store.add_documents(
        chunks,
        ids=chunk_ids,
    )

    # 返回本次写入的片段数量
    return len(chunks)