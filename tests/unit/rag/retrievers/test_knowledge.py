from unittest.mock import Mock

from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStore

from app.rag.retrievers.knowledge import (
    KnowledgeRetriever,
    create_knowledge_retriever,
)


def test_create_knowledge_retriever_uses_candidate_size() -> None:
    """验证 Retriever 使用更大的候选集，再返回配置数量。"""

    first_document = Document(
        page_content="第一条向量结果。",
        metadata={},
    )
    vector_store = Mock(spec=VectorStore)
    vector_store.similarity_search.return_value = [
        first_document,
        Document(
            page_content="第二条向量结果。",
            metadata={},
        ),
    ]
    retriever = create_knowledge_retriever(
        vector_store=vector_store,
        top_k=1,
        candidate_k=20,
    )

    assert isinstance(retriever, KnowledgeRetriever)
    assert retriever.invoke("没有词面匹配的查询") == [
        first_document,
    ]
    vector_store.similarity_search.assert_called_once_with(
        "没有词面匹配的查询",
        k=20,
    )


def test_knowledge_retriever_prioritizes_matching_tags() -> None:
    """验证精确知识标签能够纠正不理想的纯向量顺序。"""

    interview_document = Document(
        page_content="面试时先确认组织要求。",
        metadata={
            "title": "面试穿搭",
            "tags": ["面试", "正式度"],
        },
    )
    linen_document = Document(
        page_content="亚麻适合高温通勤，但需要关注褶皱。",
        metadata={
            "title": "亚麻纤维与亚麻类服装",
            "tags": ["亚麻", "高温", "褶皱"],
        },
    )
    vector_store = Mock(spec=VectorStore)
    vector_store.similarity_search.return_value = [
        interview_document,
        linen_document,
    ]
    retriever = create_knowledge_retriever(
        vector_store=vector_store,
        top_k=1,
        candidate_k=20,
    )

    results = retriever.invoke(
        "夏天通勤选择亚麻有什么注意事项？",
    )

    assert results == [linen_document]
