"""RAG 检索结果进入 Agent 上下文前的容量边界。"""

from dataclasses import dataclass

from langchain_core.documents import Document

DEFAULT_KNOWLEDGE_MAX_DOCUMENTS = 3
DEFAULT_KNOWLEDGE_MAX_FRAGMENT_CHARS = 1_200
DEFAULT_KNOWLEDGE_CONTEXT_MAX_CHARS = 4_000
_TRUNCATION_MARKER = "\n[知识片段已按预算截断]"


@dataclass(frozen=True, slots=True)
class KnowledgeContextPolicy:
    """一次检索允许注入的文档数量与字符预算。"""

    max_documents: int = DEFAULT_KNOWLEDGE_MAX_DOCUMENTS
    max_fragment_chars: int = DEFAULT_KNOWLEDGE_MAX_FRAGMENT_CHARS
    total_max_chars: int = DEFAULT_KNOWLEDGE_CONTEXT_MAX_CHARS

    def __post_init__(self) -> None:
        """所有限制都必须为正数。"""

        for field_name, value in (
            ("max_documents", self.max_documents),
            ("max_fragment_chars", self.max_fragment_chars),
            ("total_max_chars", self.total_max_chars),
        ):
            if value <= 0:
                raise ValueError(f"{field_name} 必须大于 0")


DEFAULT_KNOWLEDGE_CONTEXT_POLICY = KnowledgeContextPolicy()


@dataclass(frozen=True, slots=True)
class KnowledgeContextDiagnostics:
    """不包含查询和知识正文的 RAG 注入诊断。"""

    input_documents: int
    selected_documents: int
    omitted_documents: int
    truncated_documents: int
    selected_chars: int


@dataclass(frozen=True, slots=True)
class KnowledgeContextSelection:
    """经过容量限制后允许进入 Agent State 的知识片段。"""

    documents: tuple[Document, ...]
    diagnostics: KnowledgeContextDiagnostics


def _truncate_fragment(content: str, max_chars: int) -> str:
    """在可用字符内保留显式截断标记。"""

    if len(content) <= max_chars:
        return content
    if max_chars <= len(_TRUNCATION_MARKER):
        return content[:max_chars]
    body_chars = max_chars - len(_TRUNCATION_MARKER)
    return content[:body_chars].rstrip() + _TRUNCATION_MARKER


def select_knowledge_context(
    documents: list[Document],
    policy: KnowledgeContextPolicy = DEFAULT_KNOWLEDGE_CONTEXT_POLICY,
) -> KnowledgeContextSelection:
    """按检索顺序应用文档数、单片段和总字符限制。"""

    selected: list[Document] = []
    selected_chars = 0
    truncated_documents = 0

    for document in documents[: policy.max_documents]:
        content = document.page_content.strip()
        if not content:
            continue

        separator_chars = 2 if selected else 0
        remaining_chars = policy.total_max_chars - selected_chars - separator_chars
        if remaining_chars <= 0:
            break

        allowed_chars = min(
            policy.max_fragment_chars,
            remaining_chars,
        )
        selected_content = _truncate_fragment(
            content,
            allowed_chars,
        )
        was_truncated = len(selected_content) < len(content)
        if was_truncated:
            truncated_documents += 1

        selected.append(
            Document(
                page_content=selected_content,
                metadata=dict(document.metadata),
            )
        )
        selected_chars += separator_chars + len(selected_content)

    selected_count = len(selected)
    return KnowledgeContextSelection(
        documents=tuple(selected),
        diagnostics=KnowledgeContextDiagnostics(
            input_documents=len(documents),
            selected_documents=selected_count,
            omitted_documents=len(documents) - selected_count,
            truncated_documents=truncated_documents,
            selected_chars=selected_chars,
        ),
    )
