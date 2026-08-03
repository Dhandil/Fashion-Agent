"""OpenTelemetry 可选 Trace 和隐私边界测试。"""

from unittest.mock import Mock, patch

import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)

from app.core.config import Settings
from app.core.exceptions import ConfigurationError
from app.core.request_context import set_request_id
from app.observability import telemetry
from app.observability.telemetry import (
    _safe_span_attributes,
    initialize_telemetry,
    shutdown_telemetry,
    trace_operation,
)


def test_disabled_telemetry_creates_no_exporter() -> None:
    """验证默认关闭时不创建后台线程或网络导出器。"""

    shutdown_telemetry()
    with patch(
        "app.observability.telemetry.OTLPSpanExporter",
    ) as exporter_class:
        initialize_telemetry(
            Settings(_env_file=None),
        )

    exporter_class.assert_not_called()


def test_enabled_telemetry_requires_otlp_endpoint() -> None:
    """验证启用 Trace 时不能缺少明确 Collector 地址。"""

    shutdown_telemetry()
    settings = Settings(
        _env_file=None,
        telemetry_enabled=True,
    )

    with pytest.raises(
        ConfigurationError,
        match="TELEMETRY_OTLP_ENDPOINT",
    ):
        initialize_telemetry(settings)


def test_telemetry_initializes_and_shuts_down_provider() -> None:
    """验证配置被装配为 OTLP Exporter、采样器和显式生命周期。"""

    shutdown_telemetry()
    exporter = Mock()
    processor = Mock()
    provider = Mock(spec=TracerProvider)
    settings = Settings(
        _env_file=None,
        app_env="test",
        telemetry_enabled=True,
        telemetry_service_name="fashion-agent-test",
        telemetry_otlp_endpoint="http://collector:4317",
        telemetry_otlp_insecure=True,
        telemetry_sample_ratio=0.25,
    )

    with (
        patch(
            "app.observability.telemetry.OTLPSpanExporter",
            return_value=exporter,
        ) as exporter_class,
        patch(
            "app.observability.telemetry.BatchSpanProcessor",
            return_value=processor,
        ),
        patch(
            "app.observability.telemetry.TracerProvider",
            return_value=provider,
        ),
    ):
        initialize_telemetry(settings)
        shutdown_telemetry()

    exporter_class.assert_called_once_with(
        endpoint="http://collector:4317",
        insecure=True,
    )
    provider.add_span_processor.assert_called_once_with(processor)
    provider.shutdown.assert_called_once_with()


def test_trace_operation_exports_only_safe_attributes() -> None:
    """验证 Trace 不保存 Prompt、消息正文、密钥或异常消息。"""

    exporter = InMemorySpanExporter()
    provider = TracerProvider(shutdown_on_exit=False)
    provider.add_span_processor(
        SimpleSpanProcessor(exporter),
    )

    with (
        patch.object(
            telemetry,
            "_tracer_provider",
            provider,
        ),
        trace_operation(
            "agent.test",
            prompt="不得进入 Trace 的用户正文",
            api_key="test-secret",
            result_count=2,
        ) as observation,
    ):
        observation.add_fields(
            priority_counts={"explicit": 1},
            input_tokens=20,
        )

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    attributes = spans[0].attributes
    assert attributes["result_count"] == 2
    assert attributes["input_tokens"] == 20
    assert attributes["priority_counts"] == '{"explicit": 1}'
    assert "prompt" not in attributes
    assert "api_key" not in attributes
    provider.shutdown()


# ---- _safe_span_attributes 完整敏感字段过滤 ----

_SENSITIVE_KEYS = (
    "api_key",
    "authorization",
    "content",
    "cookie",
    "database_url",
    "message",
    "password",
    "prompt",
    "redis_url",
    "token",
)


@pytest.mark.parametrize("sensitive_key", _SENSITIVE_KEYS)
def test_safe_attributes_filters_each_sensitive_key(
    sensitive_key: str,
) -> None:
    """验证每个敏感字段无论大小写都无法进入 Span。"""
    fields = {
        sensitive_key: "secret-value",
        "result_count": 5,
    }
    cleaned = _safe_span_attributes(fields)
    assert sensitive_key not in cleaned
    assert cleaned["result_count"] == 5


@pytest.mark.parametrize("sensitive_key", _SENSITIVE_KEYS)
def test_safe_attributes_filters_uppercase_sensitive_keys(
    sensitive_key: str,
) -> None:
    """验证大小写变体同样无法绕过过滤。"""
    fields = {
        sensitive_key.upper(): "secret-value",
        "ok_field": 1,
    }
    cleaned = _safe_span_attributes(fields)
    assert sensitive_key.upper() not in cleaned
    assert cleaned["ok_field"] == 1


# ---- trace_operation 错误与请求 ID ----

_span_provider_fixture: TracerProvider | None = None


def _create_in_memory_provider() -> InMemorySpanExporter:
    """创建内存 Span Exporter 并返回 exporter 本身。"""
    global _span_provider_fixture

    _span_provider_fixture = TracerProvider(shutdown_on_exit=False)
    exporter = InMemorySpanExporter()
    _span_provider_fixture.add_span_processor(
        SimpleSpanProcessor(exporter),
    )
    return exporter


def test_trace_operation_error_does_not_leak_exception_message() -> None:
    """验证异常后 Span 只记录 error.type，不记录异常消息正文。"""

    exporter = _create_in_memory_provider()
    with patch.object(
        telemetry,
        "_tracer_provider",
        _span_provider_fixture,
    ):
        try:
            with trace_operation("agent.error_test"):
                raise ValueError("这条敏感错误消息不能进入 Trace")
        except ValueError:
            pass

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    attributes = spans[0].attributes
    assert attributes["error.type"] == "ValueError"
    assert "错误" not in str(attributes)
    assert "敏感" not in str(attributes)
    if _span_provider_fixture is not None:
        _span_provider_fixture.shutdown()


def test_trace_operation_includes_request_id_in_span() -> None:
    """验证每个 Span 自动注入当前请求的 request_id。"""

    exporter = _create_in_memory_provider()
    token = set_request_id("req-test-001")
    try:
        with patch.object(
            telemetry,
            "_tracer_provider",
            _span_provider_fixture,
        ), trace_operation("agent.request_id_test") as observation:
            observation.add_fields(count=1)

        spans = exporter.get_finished_spans()
        assert len(spans) == 1
        attributes = spans[0].attributes
        assert attributes["request_id"] == "req-test-001"
    finally:
        if _span_provider_fixture is not None:
            _span_provider_fixture.shutdown()
        token.var.reset(token)


def test_trace_operation_nested_spans_form_parent_child_chain() -> None:
    """验证嵌套 trace_operation 自动形成父子 Span 关系。"""

    exporter = _create_in_memory_provider()
    with patch.object(
        telemetry,
        "_tracer_provider",
        _span_provider_fixture,
    ), trace_operation("parent.test") as parent:
        parent.add_fields(level="outer")
        with trace_operation("child.test") as child:
            child.add_fields(level="inner")

    spans = exporter.get_finished_spans()
    assert len(spans) == 2
    # 子 Span 的 parent_id 应等于父 Span 的 id
    child_span = next(s for s in spans if s.name == "child.test")
    parent_span = next(s for s in spans if s.name == "parent.test")
    assert child_span.parent is not None
    assert child_span.parent.span_id == parent_span.context.span_id
    if _span_provider_fixture is not None:
        _span_provider_fixture.shutdown()


# ---- SpanObservation.add_fields 敏感数据过滤 ----

def test_add_fields_filters_database_url_and_redis_url() -> None:
    """验证 SpanObservation 补充字段时过滤数据库地址和 Redis 地址。"""

    exporter = _create_in_memory_provider()
    with patch.object(
        telemetry,
        "_tracer_provider",
        _span_provider_fixture,
    ), trace_operation("agent.database_test") as observation:
        observation.add_fields(
            database_url="postgresql+asyncpg://user:secret@host:5432/db",
            redis_url="redis://password@host:6379/0",
            query_count=42,
        )

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    attributes = spans[0].attributes
    assert "database_url" not in attributes
    assert "redis_url" not in attributes
    assert attributes["query_count"] == 42
    if _span_provider_fixture is not None:
        _span_provider_fixture.shutdown()


def test_add_fields_filters_content_and_message_fields() -> None:
    """验证内容、消息和 Token 字段不会通过 add_fields 进入 Span。"""

    exporter = _create_in_memory_provider()
    with patch.object(
        telemetry,
        "_tracer_provider",
        _span_provider_fixture,
    ), trace_operation("agent.content_test") as observation:
        observation.add_fields(
            content="用户消息正文",
            message="系统提示",
            token="Bearer xyz",
            authorization="Basic abc",
            password="super-secret",
            item_count=3,
        )

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    attributes = spans[0].attributes
    assert "content" not in attributes
    assert "message" not in attributes
    assert "token" not in attributes
    assert "authorization" not in attributes
    assert "password" not in attributes
    assert attributes["item_count"] == 3
    if _span_provider_fixture is not None:
        _span_provider_fixture.shutdown()


# ---- initialize_telemetry 幂等性和 Resource ----

def test_initialize_telemetry_is_idempotent() -> None:
    """验证重复调用 initialize_telemetry 不会创建第二个 Provider。"""

    shutdown_telemetry()
    exporter = Mock()
    provider = Mock(spec=TracerProvider)
    settings = Settings(
        _env_file=None,
        telemetry_enabled=True,
        telemetry_otlp_endpoint="http://collector:4317",
    )

    with (
        patch(
            "app.observability.telemetry.OTLPSpanExporter",
            return_value=exporter,
        ),
        patch(
            "app.observability.telemetry.BatchSpanProcessor",
            return_value=Mock(),
        ),
        patch(
            "app.observability.telemetry.TracerProvider",
            return_value=provider,
        ),
    ):
        initialize_telemetry(settings)
        # 第二次调用不应创建新的 Provider
        initialize_telemetry(settings)

    # TracerProvider 只创建了一次
    assert (
        telemetry._tracer_provider is provider
    ), "重复调用不应替换已有的 Provider"
    shutdown_telemetry()


def test_provider_resource_carries_service_and_environment() -> None:
    """验证 TracerProvider Resource 包含服务名和部署环境。"""

    shutdown_telemetry()
    settings = Settings(
        _env_file=None,
        app_env="staging",
        telemetry_enabled=True,
        telemetry_service_name="fashion-qa",
        telemetry_otlp_endpoint="http://collector:4317",
    )
    exporter = Mock()
    provider_mock = Mock(spec=TracerProvider)
    with (
        patch(
            "app.observability.telemetry.OTLPSpanExporter",
            return_value=exporter,
        ),
        patch(
            "app.observability.telemetry.BatchSpanProcessor",
            return_value=Mock(),
        ),
        patch(
            "app.observability.telemetry.TracerProvider",
            return_value=provider_mock,
        ) as provider_class,
    ):
        initialize_telemetry(settings)

    # 验证 Resource 参数被正确传递
    provider_class.assert_called_once()
    call_kwargs = provider_class.call_args.kwargs
    resource = call_kwargs["resource"]
    # Resource.attributes 返回 dict
    resource_attrs = resource.attributes
    assert resource_attrs["service.name"] == "fashion-qa"
    assert resource_attrs["deployment.environment.name"] == "staging"
    shutdown_telemetry()
