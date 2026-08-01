import json
import logging
from dataclasses import asdict, dataclass
from typing import Any

from langchain_core.documents import Document

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class KnowledgeDocumentReference:
    """不包含正文的知识片段引用，用于诊断和评测输出。"""

    fragment_id: str | None
    knowledge_id: str | None
    section_id: str | None
    source_path_or_url: str | None


@dataclass(frozen=True, slots=True)
class KnowledgeRetrievalDiagnostics:
    """一次知识检索的非敏感诊断数据。"""

    candidate_count: int
    before_rerank: tuple[KnowledgeDocumentReference, ...]
    after_rerank: tuple[KnowledgeDocumentReference, ...]
    final_sources: tuple[KnowledgeDocumentReference, ...]
    empty_result_reason: str | None
    duration_ms: float


def create_document_reference(
    document: Document,
) -> KnowledgeDocumentReference:
    """从文档元数据创建不含知识正文的稳定引用。"""

    metadata = document.metadata
    source = metadata.get("source_path_or_url") or metadata.get("source")

    return KnowledgeDocumentReference(
        fragment_id=_optional_string(
            metadata.get("fragment_id"),
        ),
        knowledge_id=_optional_string(
            metadata.get("knowledge_id"),
        ),
        section_id=_optional_string(
            metadata.get("section_id"),
        ),
        source_path_or_url=_optional_string(source),
    )


def log_knowledge_retrieval_diagnostics(
    diagnostics: KnowledgeRetrievalDiagnostics,
) -> None:
    """通过标准日志记录结构化检索事件，不记录用户问题和知识正文。"""

    diagnostics_data = _diagnostics_to_dict(diagnostics)
    logger.info(
        "knowledge_retrieval_completed | %s",
        json.dumps(
            diagnostics_data,
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        extra={
            "event": "knowledge_retrieval_completed",
            "rag_diagnostics": diagnostics_data,
        },
    )


def _optional_string(value: object) -> str | None:
    """把存在的元数据转换为字符串，空值保持为 None。"""

    if value is None:
        return None

    normalized = str(value).strip()
    return normalized or None


def _diagnostics_to_dict(
    diagnostics: KnowledgeRetrievalDiagnostics,
) -> dict[str, Any]:
    """把不可变诊断对象转换成日志系统容易处理的字典。"""

    return asdict(diagnostics)
