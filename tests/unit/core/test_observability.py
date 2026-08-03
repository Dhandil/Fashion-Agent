"""基础结构化操作观测测试。"""

import logging
from unittest.mock import patch

import pytest

from app.core.observability import (
    anonymize_identifier,
    observe_operation,
)


def test_anonymize_identifier_is_stable_without_exposing_input() -> None:
    """验证同一进程可以关联 ID，同时日志值不包含原始标识。"""

    first = anonymize_identifier("user-sensitive-001")
    repeated = anonymize_identifier("user-sensitive-001")
    other = anonymize_identifier("user-sensitive-002")

    assert first == repeated
    assert first != other
    assert len(first) == 16
    assert "user-sensitive" not in first


def test_observe_operation_records_completion_fields() -> None:
    """验证成功操作包含用途、结果数量和非负耗时。"""

    logger = logging.getLogger("test-observability-success")

    with (
        patch(
            "app.core.observability.log_event",
        ) as mocked_log_event,
        observe_operation(
            logger,
            "agent.tool",
            tool_name="search_wardrobe",
        ) as observation,
    ):
        observation.add_fields(result_count=3)

    mocked_log_event.assert_called_once()
    call = mocked_log_event.call_args
    assert call.args == (
        logger,
        "agent.tool.completed",
    )
    assert call.kwargs["tool_name"] == "search_wardrobe"
    assert call.kwargs["result_count"] == 3
    assert call.kwargs["duration_ms"] >= 0


def test_observe_operation_records_failure_and_reraises() -> None:
    """验证失败操作记录异常类型后仍把原异常交给业务边界。"""

    logger = logging.getLogger("test-observability-failure")

    with (
        patch(
            "app.core.observability.log_event",
        ) as mocked_log_event,
        pytest.raises(
            RuntimeError,
            match="测试失败",
        ),
        observe_operation(
            logger,
            "agent.llm",
            purpose="chat",
        ),
    ):
        raise RuntimeError("测试失败")

    mocked_log_event.assert_called_once()
    call = mocked_log_event.call_args
    assert call.args == (
        logger,
        "agent.llm.failed",
    )
    assert call.kwargs["level"] == logging.ERROR
    assert call.kwargs["purpose"] == "chat"
    assert call.kwargs["error_type"] == "RuntimeError"
    assert call.kwargs["duration_ms"] >= 0
