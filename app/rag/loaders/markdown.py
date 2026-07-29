from pathlib import Path

from langchain_core.documents import Document


def load_markdown_documents(
    directory: Path,
) -> list[Document]:
    """加载目录下所有非空 Markdoown 文档。"""

    documents: list[Document] = []

    # 递归查找目录及子目录中的所有 .md 文件
    for file_path in sorted(directory.rglob("*.md")):
        # 使用 UTF-8 读取中文知识文档
        content = file_path.read_text(encoding="utf-8")

        # 跳过只有空格或换行的空文档
        if not content.strip():
            continue

        # 转换成 LangChain Document，并保留来源路径
        documents.append(
            Document(
                page_content=content,
                metadata={
                    "source":str(file_path),
                },
            )
        )

    return documents