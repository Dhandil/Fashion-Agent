import re
from typing import Any

from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.vectorstores import VectorStore
from pydantic import ConfigDict, Field

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
        return tuple(
            str(tag).strip().lower()
            for tag in raw_tags
            if str(tag).strip()
        )
    if isinstance(raw_tags, str) and raw_tags.strip():
        return (raw_tags.strip().lower(),)
    return ()


def _rerank_score(
    query: str,
    query_terms: set[str],
    document: Document,
    vector_rank: int,
) -> tuple[int, int, int, int]:
    """组合治理元数据、正文词面匹配和原始向量顺序。"""

    normalized_query = query.lower()
    tag_hits = sum(
        1
        for tag in _metadata_tags(document.metadata)
        if len(tag) >= 2 and tag in normalized_query
    )
    title_terms = _extract_search_terms(
        str(document.metadata.get("title", "")),
    )
    content_terms = _extract_search_terms(
        document.page_content,
    )

    return (
        tag_hits,
        len(query_terms & title_terms),
        len(query_terms & content_terms),
        -vector_rank,
    )


class KnowledgeRetriever(BaseRetriever):
    """先做向量召回，再利用知识治理元数据进行轻量混合重排。"""

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )

    vector_store: VectorStore
    top_k: int = Field(gt=0)
    candidate_k: int = Field(gt=0)

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> list[Document]:
        """召回候选并返回本地重排后的前 top_k 个片段。"""

        del run_manager
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

        return [
            document
            for _, document in ranked_candidates[: self.top_k]
        ]


def create_knowledge_retriever(
    vector_store: VectorStore,
    top_k: int = 3,
    candidate_k: int = 24,
) -> KnowledgeRetriever:
    """创建具有可配置候选规模的服装知识 Retriever。"""

    return KnowledgeRetriever(
        vector_store=vector_store,
        top_k=top_k,
        candidate_k=max(top_k, candidate_k),
    )
