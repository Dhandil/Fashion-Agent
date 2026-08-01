import logging
import re
from collections.abc import Callable
from time import perf_counter
from typing import Any

from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.vectorstores import VectorStore
from pydantic import ConfigDict, Field

from app.rag.retrievers.diagnostics import (
    KnowledgeRetrievalDiagnostics,
    create_document_reference,
    log_knowledge_retrieval_diagnostics,
)

logger = logging.getLogger(__name__)

KnowledgeRetrievalObserver = Callable[
    [KnowledgeRetrievalDiagnostics],
    None,
]

_CJK_SEQUENCE_PATTERN = re.compile(r"[\u4e00-\u9fff]+")
_WORD_PATTERN = re.compile(r"[a-zA-Z0-9_]{2,}")


def _extract_search_terms(text: str) -> set[str]:
    """提取英文单词和中文二至四字片段，用于轻量本地重排。"""

    normalized_text = text.lower()
    terms = set(_WORD_PATTERN.findall(normalized_text))

    for sequence in _CJK_SEQUENCE_PATTERN.findall(
        normalized_text,
    ):
        for length in (2, 3, 4):
            terms.update(
                sequence[index : index + length]
                for index in range(
                    len(sequence) - length + 1,
                )
            )

    return terms


def _metadata_tags(metadata: dict[str, Any]) -> tuple[str, ...]:
    """兼容 Chroma 返回的标签列表和旧字符串元数据。"""

    raw_tags = metadata.get("tags", ())
    if isinstance(raw_tags, list):
        return tuple(str(tag).strip().lower() for tag in raw_tags if str(tag).strip())
    if isinstance(raw_tags, str) and raw_tags.strip():
        return (raw_tags.strip().lower(),)
    return ()


def _rerank_score(
    query: str,
    query_terms: set[str],
    document: Document,
    vector_rank: int,
) -> float:
    """在保留向量排序主干的前提下，用有上限的词面信号微调。"""

    normalized_query = query.lower()
    tag_hits = sum(
        1 for tag in _metadata_tags(document.metadata) if len(tag) >= 2 and tag in normalized_query
    )
    title_terms = _extract_search_terms(
        str(document.metadata.get("title", "")),
    )
    content_terms = _extract_search_terms(
        document.page_content,
    )

    # 向量库只返回排名而没有原始相似度，因此使用排名作为稳定主干。
    # 标签、标题和正文只提供有限加分，避免远处候选因一个通用词跃升到首位。
    return (
        -float(vector_rank)
        + min(tag_hits, 2) * 2.0
        + min(len(query_terms & title_terms), 4) * 0.5
        + min(len(query_terms & content_terms), 8) * 0.125
    )


class KnowledgeRetriever(BaseRetriever):
    """先做向量召回，再利用知识治理元数据进行轻量混合重排。"""

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )

    vector_store: VectorStore
    top_k: int = Field(gt=0)
    candidate_k: int = Field(gt=0)
    diagnostics_observer: KnowledgeRetrievalObserver

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> list[Document]:
        """召回候选并返回本地重排后的前 top_k 个片段。"""

        del run_manager
        started_at = perf_counter()
        candidates = self.vector_store.similarity_search(
            query,
            k=max(self.top_k, self.candidate_k),
        )
        query_terms = _extract_search_terms(query)
        ranked_candidates = sorted(
            enumerate(candidates),
            key=lambda item: _rerank_score(
                query=query,
                query_terms=query_terms,
                document=item[1],
                vector_rank=item[0],
            ),
            reverse=True,
        )

        results = [document for _, document in ranked_candidates[: self.top_k]]
        diagnostics = KnowledgeRetrievalDiagnostics(
            candidate_count=len(candidates),
            before_rerank=tuple(create_document_reference(document) for document in candidates),
            after_rerank=tuple(
                create_document_reference(document) for _, document in ranked_candidates
            ),
            final_sources=tuple(create_document_reference(document) for document in results),
            empty_result_reason=("vector_store_returned_no_candidates" if not candidates else None),
            duration_ms=round(
                (perf_counter() - started_at) * 1000,
                3,
            ),
        )
        self._emit_diagnostics(diagnostics)

        return results

    def _emit_diagnostics(
        self,
        diagnostics: KnowledgeRetrievalDiagnostics,
    ) -> None:
        """发送诊断事件；观察器故障不能中断正常检索。"""

        try:
            self.diagnostics_observer(diagnostics)
        except Exception:
            logger.warning(
                "知识检索诊断观察器执行失败。",
                exc_info=True,
            )


def create_knowledge_retriever(
    vector_store: VectorStore,
    top_k: int = 3,
    candidate_k: int = 24,
    diagnostics_observer: KnowledgeRetrievalObserver = (log_knowledge_retrieval_diagnostics),
) -> KnowledgeRetriever:
    """创建具有可配置候选规模的服装知识 Retriever。"""

    return KnowledgeRetriever(
        vector_store=vector_store,
        top_k=top_k,
        candidate_k=max(top_k, candidate_k),
        diagnostics_observer=diagnostics_observer,
    )
