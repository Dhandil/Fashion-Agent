from pathlib import Path

from app.rag.loaders.markdown import load_markdown_documents


def test_load_markdown_documents(
    tmp_path: Path,
) -> None:
    """验证 Markdown 文档加载和空文件过滤。"""

    # 创建临时子目录
    fabrics_directory = tmp_path / "fabrics"
    fabrics_directory.mkdir()

    # 创建两份有效中文知识文档
    (tmp_path / "summer.md").write_text(
        "亚麻面料透气，适合夏季穿着。",
        encoding="utf-8",
    )
    (fabrics_directory / "winter.md").write_text(
        "羊毛面料保暖，适合秋冬穿着。",
        encoding="utf-8",
    )

    # 创建一份只有空白字符的文档
    (tmp_path / "empty.md").write_text(
        "   \n",
        encoding="utf-8",
    )

    # 加载临时目录中的 Markdown 文件
    documents = load_markdown_documents(tmp_path)

    # 空文档应被跳过，只保留两份有效文档
    assert len(documents) == 2

    # 验证中文内容被正确读取
    document_contents = {
        document.page_content for document in documents
    }
    assert document_contents == {
        "亚麻面料透气，适合夏季穿着。",
        "羊毛面料保暖，适合秋冬穿着。",
    }

    # 每份文档都应该保留来源文件路径
    assert all(
        "source" in document.metadata
        for document in documents
    )