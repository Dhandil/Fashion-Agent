from unittest.mock import Mock

from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStore

from app.rag.retrievers.diagnostics import (
    KnowledgeRetrievalDiagnostics,
)
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


def test_knowledge_retriever_keeps_strong_vector_match() -> None:
    """验证远处候选不能只靠通用词面命中覆盖强向量结果。"""

    wind_document = Document(
        page_content="大风环境需要区分防风外层和保温层。",
        metadata={
            "title": "风、风寒与外层防护边界",
            "tags": ["防风层"],
        },
    )
    temperature_document = Document(
        page_content=("气温不低时也要结合活动、外层、风和体感温度进行判断。"),
        metadata={
            "title": "气温、体感与服装热舒适",
            "tags": ["气温", "外层"],
        },
    )
    vector_store = Mock(spec=VectorStore)
    vector_store.similarity_search.return_value = [
        wind_document,
        *[
            Document(
                page_content=f"中间候选 {index}",
                metadata={},
            )
            for index in range(5)
        ],
        temperature_document,
    ]
    retriever = create_knowledge_retriever(
        vector_store=vector_store,
        top_k=1,
        candidate_k=7,
    )

    results = retriever.invoke(
        "气温不算低但风很大，为什么还要考虑防风外层？",
    )

    assert results == [wind_document]


def test_knowledge_retriever_preserves_relevant_top_candidate() -> None:
    """验证正确的向量第一名不会被宽泛核心结论挤出返回范围。"""

    care_document = Document(
        page_content="热、湿和机械作用可能使羊毛毡化或尺寸变化。",
        metadata={
            "title": "羊毛护理、尺寸与识别",
            "tags": ["羊毛", "护理"],
        },
    )
    broad_document = Document(
        page_content="羊毛衣服具有多种特点，清洗和缩水需要结合标签判断。",
        metadata={
            "title": "羊毛核心结论",
            "tags": ["羊毛"],
        },
    )
    vector_store = Mock(spec=VectorStore)
    vector_store.similarity_search.return_value = [
        care_document,
        broad_document,
    ]
    retriever = create_knowledge_retriever(
        vector_store=vector_store,
        top_k=1,
        candidate_k=2,
    )

    results = retriever.invoke(
        "羊毛衣服清洗时怎样避免缩水和毡化？",
    )

    assert results == [care_document]


def test_knowledge_retriever_emits_non_sensitive_diagnostics() -> None:
    """验证诊断事件包含重排顺序和来源，但不保存用户问题正文。"""

    interview_document = Document(
        page_content="面试时先确认组织要求。",
        metadata={
            "fragment_id": "fk-interview::S01::001",
            "knowledge_id": "fk-interview",
            "section_id": "S01",
            "source_path_or_url": "knowledge/interview.md",
            "tags": ["面试"],
        },
    )
    linen_document = Document(
        page_content="亚麻适合炎热天气。",
        metadata={
            "fragment_id": "fk-linen::S02::001",
            "knowledge_id": "fk-linen",
            "section_id": "S02",
            "source_path_or_url": "knowledge/linen.md",
            "tags": ["亚麻"],
        },
    )
    vector_store = Mock(spec=VectorStore)
    vector_store.similarity_search.return_value = [
        interview_document,
        linen_document,
    ]
    events: list[KnowledgeRetrievalDiagnostics] = []
    retriever = create_knowledge_retriever(
        vector_store=vector_store,
        top_k=1,
        candidate_k=2,
        diagnostics_observer=events.append,
    )

    results = retriever.invoke("夏天穿亚麻有什么优点？")

    assert results == [linen_document]
    assert len(events) == 1
    diagnostics = events[0]
    assert diagnostics.candidate_count == 2
    assert diagnostics.before_rerank[0].fragment_id == ("fk-interview::S01::001")
    assert diagnostics.after_rerank[0].fragment_id == ("fk-linen::S02::001")
    assert diagnostics.final_sources == (diagnostics.after_rerank[0],)
    assert diagnostics.empty_result_reason is None
    assert diagnostics.duration_ms >= 0
    assert not hasattr(diagnostics, "query")


def test_knowledge_retriever_records_empty_result_reason() -> None:
    """验证向量库没有候选时记录明确原因。"""

    vector_store = Mock(spec=VectorStore)
    vector_store.similarity_search.return_value = []
    events: list[KnowledgeRetrievalDiagnostics] = []
    retriever = create_knowledge_retriever(
        vector_store=vector_store,
        diagnostics_observer=events.append,
    )

    assert retriever.invoke("不存在的知识") == []
    assert events[0].candidate_count == 0
    assert events[0].before_rerank == ()
    assert events[0].after_rerank == ()
    assert events[0].final_sources == ()
    assert events[0].empty_result_reason == ("vector_store_returned_no_candidates")
