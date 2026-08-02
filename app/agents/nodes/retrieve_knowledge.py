import logging
from collections.abc import Callable

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

from app.agents.context_package import ContextProvenance
from app.agents.knowledge_context import (
    DEFAULT_KNOWLEDGE_CONTEXT_POLICY,
    KnowledgeContextPolicy,
    select_knowledge_context,
)
from app.agents.state.shopping import ShoppingAgentState
from app.core.observability import (
    log_event,
    observe_operation,
)

logger = logging.getLogger(__name__)
KnowledgeRetrievalResult = dict[
    str,
    str | list[str] | list[ContextProvenance],
]


def _optional_metadata_string(
    document: Document,
    key: str,
) -> str | None:
    """把可选文档元数据安全转换为非空字符串。"""

    value = document.metadata.get(key)
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _build_knowledge_provenance(
    document: Document,
) -> ContextProvenance | None:
    """从检索文档中提取与正文分离的来源元数据。"""

    reference_id = _optional_metadata_string(
        document,
        "fragment_id",
    ) or _optional_metadata_string(document, "knowledge_id")
    source_path = _optional_metadata_string(
        document,
        "source_path_or_url",
    ) or _optional_metadata_string(document, "source")
    if reference_id is None and source_path is None:
        return None
    return ContextProvenance(
        reference_id=reference_id,
        source_path_or_url=source_path,
        version=_optional_metadata_string(document, "version"),
        updated_at=_optional_metadata_string(document, "updated_at"),
    )


def _format_knowledge_source(
    document: Document,
) -> str | None:
    """生成一条可追溯到具体命中片段的知识来源。"""

    fragment_id = document.metadata.get("fragment_id")
    source_path = (
        document.metadata.get("source_path_or_url")
        or document.metadata.get("source")
    )

    reference_parts = [
        str(value)
        for value in (fragment_id, source_path)
        if value
    ]
    for metadata_key in (
        "knowledge_id",
        "version",
        "updated_at",
    ):
        if metadata_value := document.metadata.get(metadata_key):
            reference_parts.append(
                f"{metadata_key}={metadata_value}",
            )
    return " | ".join(reference_parts) or None


def create_retrieve_knowledge_node(
    retriever: BaseRetriever,
    context_policy: KnowledgeContextPolicy = (
        DEFAULT_KNOWLEDGE_CONTEXT_POLICY
    ),
) -> Callable[[ShoppingAgentState], KnowledgeRetrievalResult]:
    """创建已经绑定 Retriever 的知识检索节点。"""

    def retriever_knowledge(
        state: ShoppingAgentState,
    ) -> KnowledgeRetrievalResult:
        """根据最新用户消息检索服装知识。"""

        # 读取当前 State 中的最后一条消息
        latest_message = state["messages"][-1]

        # 将消息内容转换成检索查询字符串
        query = str(latest_message.content)

        # 从向量库检索相关知识文档
        with observe_operation(
            logger,
            "agent.rag",
            purpose="knowledge_retrieval",
        ) as observation:
            retrieved_documents = retriever.invoke(query)
            selection = select_knowledge_context(
                retrieved_documents,
                context_policy,
            )
            observation.add_fields(
                retrieved_documents=len(
                    retrieved_documents,
                ),
                selected_documents=len(
                    selection.documents,
                ),
                empty_result=not selection.documents,
            )
        documents = selection.documents

        # 将多个文档片段组合成模型可阅读的上下文
        knowledge_context = "\n\n".join(
            document.page_content
            for document in documents
        )

        # 每个命中片段都输出一条来源，方便核对检索依据
        knowledge_sources = [
            source
            for document in documents
            if (
                source := _format_knowledge_source(
                    document,
                )
            )
        ]
        knowledge_provenance = [
            provenance
            for document in documents
            if (
                provenance := _build_knowledge_provenance(
                    document,
                )
            )
            is not None
        ]

        diagnostics = selection.diagnostics
        log_event(
            logger,
            "agent.knowledge_context.selected",
            input_documents=diagnostics.input_documents,
            selected_documents=diagnostics.selected_documents,
            omitted_documents=diagnostics.omitted_documents,
            truncated_documents=(
                diagnostics.truncated_documents
            ),
            selected_chars=diagnostics.selected_chars,
            source_count=len(knowledge_sources),
        )

        return {
            "knowledge_context": knowledge_context,
            "knowledge_sources": knowledge_sources,
            "knowledge_provenance": knowledge_provenance,
        }

    return retriever_knowledge
