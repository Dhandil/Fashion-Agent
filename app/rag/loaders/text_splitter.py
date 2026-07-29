from langchain_text_splitters import RecursiveCharacterTextSplitter


def create_text_splitter(
    chunk_size: int = 400,
    chunk_overlap: int = 50,
) -> RecursiveCharacterTextSplitter:
    """创建适合中文服装知识的递归文本切分器。"""

    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=[
            "\n\n",
            "\n",
            "。",
            "！",
            "？",
            "；",
            "，",
            " ",
            "",
        ],
    )