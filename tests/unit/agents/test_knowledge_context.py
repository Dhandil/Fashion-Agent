import pytest
from langchain_core.documents import Document

from app.agents.knowledge_context import (
    KnowledgeContextPolicy,
    select_knowledge_context,
)


def test_select_knowledge_context_applies_all_limits() -> None:
    """验证文档数、单片段和总字符限制同时生效。"""

    documents = [
        Document(
            page_content=character * 100,
            metadata={"fragment_id": f"fragment-{index}"},
        )
        for index, character in enumerate("甲乙丙丁", start=1)
    ]

    selection = select_knowledge_context(
        documents,
        KnowledgeContextPolicy(
            max_documents=3,
            max_fragment_chars=60,
            total_max_chars=100,
        ),
    )

    assert len(selection.documents) == 2
    assert selection.documents[0].metadata == {
        "fragment_id": "fragment-1",
    }
    assert "[知识片段已按预算截断]" in (
        selection.documents[0].page_content
    )
    assert selection.diagnostics.input_documents == 4
    assert selection.diagnostics.selected_documents == 2
    assert selection.diagnostics.omitted_documents == 2
    assert selection.diagnostics.truncated_documents == 2
    assert selection.diagnostics.selected_chars <= 100


def test_select_knowledge_context_ignores_empty_document() -> None:
    """验证空片段不会占用上下文名额或字符预算。"""

    selection = select_knowledge_context(
        [
            Document(page_content="   "),
            Document(page_content="亚麻透气。"),
        ],
    )

    assert [
        document.page_content
        for document in selection.documents
    ] == ["亚麻透气。"]
    assert selection.diagnostics.omitted_documents == 1


@pytest.mark.parametrize(
    "field_name",
    [
        "max_documents",
        "max_fragment_chars",
        "total_max_chars",
    ],
)
def test_knowledge_context_policy_rejects_zero(
    field_name: str,
) -> None:
    """验证容量边界不能被配置为零。"""

    values = {
        "max_documents": 3,
        "max_fragment_chars": 1_200,
        "total_max_chars": 4_000,
    }
    values[field_name] = 0

    with pytest.raises(ValueError, match="必须大于 0"):
        KnowledgeContextPolicy(**values)
