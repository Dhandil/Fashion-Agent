from pathlib import Path
from unittest.mock import Mock

from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStore
from langchain_text_splitters.base import TextSplitter

from app.rag.ingestion import index_markdown_directory


def test_index_markdown_directory_adds_chunks(
    tmp_path: Path,
) -> None:
    """验证 Markdown 文档经过切分后写入向量库。"""

    # 创建一份临时知识文档
    knowledge_file = tmp_path / "fabrics.md"
    knowledge_file.write_text(
        "亚麻适合夏季。羊毛适合冬季。",
        encoding="utf-8",
    )

    # 创建假的切分器和向量库
    text_splitter = Mock(spec=TextSplitter)
    vector_store = Mock(spec=VectorStore)

    # 模拟切分器返回两个文档片段
    chunks = [
        Document(
            page_content="亚麻适合夏季。",
            metadata={"source": str(knowledge_file)},
        ),
        Document(
            page_content="羊毛适合冬季。",
            metadata={"source": str(knowledge_file)},
        ),
    ]
    text_splitter.split_documents.return_value = chunks

    # 执行知识入库流程
    indexed_count = index_markdown_directory(
        directory=tmp_path,
        text_splitter=text_splitter,
        vector_store=vector_store,
    )

    # 验证返回的索引数量
    assert indexed_count == 2

    # 验证切分器被调用了一次
    text_splitter.split_documents.assert_called_once()

    # 取得 Loader 传给切分器的原始文档
    loaded_documents = (
        text_splitter.split_documents.call_args.args[0]
    )

    # 验证 Loader 成功读取临时知识文档
    assert len(loaded_documents) == 1
    assert loaded_documents[0].page_content == (
        "亚麻适合夏季。羊毛适合冬季。"
    )

    # 验证向量库只执行了一次写入
    vector_store.add_documents.assert_called_once()

    # 读取写入时的位置参数和关键字参数
    add_documents_call = vector_store.add_documents.call_args
    written_chunks = add_documents_call.args[0]
    written_ids = add_documents_call.kwargs["ids"]

    # 验证写入的片段没有发生变化
    assert written_chunks == chunks

    # 两个片段应该分别拥有一个 ID
    assert len(written_ids) == 2

    # 不同内容的片段应该生成不同 ID
    assert written_ids[0] != written_ids[1]

    # SHA-256 的十六进制结果长度固定为 64
    assert all(len(chunk_id) == 64 for chunk_id in written_ids)