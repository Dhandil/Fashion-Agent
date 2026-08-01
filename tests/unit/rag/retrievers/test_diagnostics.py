import logging

from _pytest.logging import LogCaptureFixture

from app.rag.retrievers.diagnostics import (
    KnowledgeRetrievalDiagnostics,
    log_knowledge_retrieval_diagnostics,
)


def test_diagnostics_log_contains_structured_non_sensitive_data(
    caplog: LogCaptureFixture,
) -> None:
    """验证默认日志能看到诊断字段，同时不包含查询或知识正文。"""

    diagnostics = KnowledgeRetrievalDiagnostics(
        candidate_count=0,
        before_rerank=(),
        after_rerank=(),
        final_sources=(),
        empty_result_reason="vector_store_returned_no_candidates",
        duration_ms=1.25,
    )

    # pytest 的 caplog 由测试框架注入；这里通过标准日志接口捕获事件。
    with caplog.at_level(
        logging.INFO,
        logger="app.rag.retrievers.diagnostics",
    ):
        log_knowledge_retrieval_diagnostics(diagnostics)

    record = caplog.records[0]
    assert record.__dict__["event"] == "knowledge_retrieval_completed"
    assert record.__dict__["rag_diagnostics"]["candidate_count"] == 0
    assert '"candidate_count":0' in record.getMessage()
    assert "query" not in record.getMessage()
    assert "page_content" not in record.getMessage()
