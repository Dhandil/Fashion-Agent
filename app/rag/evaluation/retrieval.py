import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from langchain_core.documents import Document

from app.rag.evaluation.models import (
    RetrievalEvaluationCase,
    RetrievalEvaluationSuite,
)
from app.rag.retrievers.diagnostics import (
    KnowledgeDocumentReference,
    create_document_reference,
)


@dataclass(frozen=True, slots=True)
class RetrievalCaseResult:
    """单条检索问题的来源命中结果。"""

    case_id: str
    passed: bool
    knowledge_rank: int | None
    section_rank: int | None
    returned_sources: tuple[KnowledgeDocumentReference, ...]


@dataclass(frozen=True, slots=True)
class RetrievalEvaluationReport:
    """完整问题集的聚合评测结果。"""

    release_id: str
    results: tuple[RetrievalCaseResult, ...]

    @property
    def total_count(self) -> int:
        """返回评测问题总数。"""

        return len(self.results)

    @property
    def passed_count(self) -> int:
        """返回同时命中预期知识和章节的问题数。"""

        return sum(result.passed for result in self.results)

    @property
    def pass_rate(self) -> float:
        """返回零到一之间的通过率。"""

        if not self.results:
            return 0.0
        return self.passed_count / self.total_count


def load_retrieval_evaluation_suite(
    path: Path,
) -> RetrievalEvaluationSuite:
    """从可提交的 JSON 文件加载并校验检索问题集。"""

    raw_data = json.loads(path.read_text(encoding="utf-8"))
    return RetrievalEvaluationSuite.model_validate(raw_data)


def evaluate_retrieval_case(
    case: RetrievalEvaluationCase,
    documents: Sequence[Document],
) -> RetrievalCaseResult:
    """判断限定排名内是否命中预期知识及稳定章节。"""

    limited_documents = documents[: case.max_rank]
    references = tuple(create_document_reference(document) for document in limited_documents)
    knowledge_rank: int | None = None
    section_rank: int | None = None

    for rank, reference in enumerate(references, start=1):
        if reference.knowledge_id != case.expected_knowledge_id:
            continue

        if knowledge_rank is None:
            knowledge_rank = rank
        if reference.section_id in case.expected_section_ids:
            section_rank = rank
            break

    return RetrievalCaseResult(
        case_id=case.case_id,
        passed=section_rank is not None,
        knowledge_rank=knowledge_rank,
        section_rank=section_rank,
        returned_sources=references,
    )


def evaluate_retrieval_suite(
    suite: RetrievalEvaluationSuite,
    retrieve_documents: Callable[[str], Sequence[Document]],
) -> RetrievalEvaluationReport:
    """逐条执行问题集，并保留每条问题实际命中的知识来源。"""

    results = tuple(
        evaluate_retrieval_case(
            case,
            retrieve_documents(case.query),
        )
        for case in suite.cases
    )
    return RetrievalEvaluationReport(
        release_id=suite.release_id,
        results=results,
    )
