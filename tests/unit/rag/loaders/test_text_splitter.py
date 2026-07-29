from app.rag.loaders.text_splitter import create_text_splitter


def test_text_splitter_respects_size_and_overlap() -> None:
    """验证文本切分长度和重叠内容。"""

    # 创建较小参数的切分器，方便测试
    splitter = create_text_splitter(
        chunk_size=100,
        chunk_overlap=20,
    )

    # 创建长度为 250 的连续测试文本
    text = "0123456789" * 25

    # 将完整文本切分成多个字符串片段
    chunks = splitter.split_text(text)

    # 应该产生多个片段
    assert len(chunks) > 1

    # 每个片段都不能超过 chunk_size
    assert all(len(chunk) <= 100 for chunk in chunks)

    # 第一段末尾 20 个字符应出现在第二段开头
    assert chunks[0][-20:] == chunks[1][:20]