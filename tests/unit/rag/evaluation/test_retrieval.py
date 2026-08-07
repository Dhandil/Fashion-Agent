from pathlib import Path

from langchain_core.documents import Document

from app.rag.evaluation.models import (
    RetrievalEvaluationCase,
    RetrievalEvaluationSuite,
)
from app.rag.evaluation.retrieval import (
    evaluate_retrieval_case,
    evaluate_retrieval_suite,
    load_retrieval_evaluation_suite,
)


def _document(
    *,
    knowledge_id: str,
    section_id: str,
    fragment_id: str,
) -> Document:
    """创建带有正式知识身份的最小测试文档。"""

    return Document(
        page_content="测试知识正文。",
        metadata={
            "fragment_id": fragment_id,
            "knowledge_id": knowledge_id,
            "section_id": section_id,
            "source_path_or_url": "knowledge/test.md",
        },
    )


def test_committed_evaluation_suite_covers_core_categories() -> None:
    """验证可提交问题集有效，并覆盖当前四类核心知识。"""

    suite = load_retrieval_evaluation_suite(
        Path("evaluation/rag/retrieval_cases.json"),
    )

    assert suite.release_id == "fashion-knowledge-2.8.0"
    # 问题集覆盖四类核心知识，且会随知识库增长（当前 16 条）
    assert len(suite.cases) >= 8
    assert {case.category for case in suite.cases} == {
        "material",
        "occasion",
        "weather",
        "care",
    }


def test_evaluate_retrieval_case_requires_expected_section() -> None:
    """验证只命中知识文档但章节不相关时不能通过。"""

    case = RetrievalEvaluationCase(
        case_id="linen-care",
        category="material",
        query="亚麻怎么护理？",
        expected_knowledge_id="fk-materials-linen-001",
        expected_section_ids=("S06",),
        max_rank=2,
    )
    documents = [
        _document(
            knowledge_id="fk-materials-linen-001",
            section_id="S02",
            fragment_id="fk-materials-linen-001::S02::001",
        ),
        _document(
            knowledge_id="fk-materials-cotton-001",
            section_id="S03",
            fragment_id="fk-materials-cotton-001::S03::001",
        ),
    ]

    result = evaluate_retrieval_case(case, documents)

    assert result.passed is False
    assert result.knowledge_rank == 1
    assert result.section_rank is None
    assert result.returned_sources[0].fragment_id == ("fk-materials-linen-001::S02::001")


def test_evaluate_retrieval_suite_reports_pass_rate() -> None:
    """验证问题集汇总通过率并保留每次实际命中来源。"""

    cases = (
        RetrievalEvaluationCase(
            case_id="linen",
            category="material",
            query="亚麻问题",
            expected_knowledge_id="fk-materials-linen-001",
            expected_section_ids=("S02",),
        ),
        RetrievalEvaluationCase(
            case_id="rain",
            category="weather",
            query="降雨问题",
            expected_knowledge_id="fk-weather-rain-protection-001",
            expected_section_ids=("S03",),
        ),
    )
    suite = RetrievalEvaluationSuite(
        schema_version="1.0",
        release_id="test-release",
        cases=cases,
    )
    results_by_query = {
        "亚麻问题": [
            _document(
                knowledge_id="fk-materials-linen-001",
                section_id="S02",
                fragment_id="fk-materials-linen-001::S02::001",
            ),
        ],
        "降雨问题": [],
    }

    report = evaluate_retrieval_suite(
        suite=suite,
        retrieve_documents=results_by_query.__getitem__,
    )

    assert report.total_count == 2
    assert report.passed_count == 1
    assert report.pass_rate == 0.5
    assert report.results[0].returned_sources[0].knowledge_id == ("fk-materials-linen-001")
    assert report.results[1].returned_sources == ()
