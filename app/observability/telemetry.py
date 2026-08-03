"""默认关闭、显式配置的 OpenTelemetry Trace 生命周期。"""

import json
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased
from opentelemetry.trace import Span, Status, StatusCode, Tracer
from opentelemetry.util.types import AttributeValue

from app.core.config import Settings, get_settings
from app.core.exceptions import ConfigurationError
from app.core.request_context import get_request_id

_tracer_provider: TracerProvider | None = None

# 这些字段无论调用方是否误传都不进入 Trace；Token 数量使用单独的 *_tokens 字段。
_SENSITIVE_ATTRIBUTE_KEYS = frozenset(
    {
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
    },
)


def _normalise_attribute_value(value: Any) -> AttributeValue | None:
    """把复杂诊断字段转换为 OpenTelemetry 支持的非敏感属性类型。"""

    if value is None:
        return None
    if isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, (list, tuple)) and all(
        isinstance(item, (str, bool, int, float)) for item in value
    ):
        return tuple(value)
    return json.dumps(
        value,
        ensure_ascii=False,
        default=str,
        sort_keys=True,
    )


def _safe_span_attributes(
    fields: dict[str, Any],
) -> dict[str, AttributeValue]:
    """丢弃敏感字段并规范化其余诊断数据。"""

    attributes: dict[str, AttributeValue] = {}
    for key, value in fields.items():
        if key.lower() in _SENSITIVE_ATTRIBUTE_KEYS:
            continue
        normalised = _normalise_attribute_value(value)
        if normalised is not None:
            attributes[key] = normalised
    return attributes


def initialize_telemetry(
    settings: Settings | None = None,
) -> None:
    """按配置创建 OTLP TracerProvider；关闭时不创建线程或网络客户端。"""

    global _tracer_provider

    resolved_settings = settings or get_settings()
    if not resolved_settings.telemetry_enabled:
        return
    if _tracer_provider is not None:
        return
    if resolved_settings.telemetry_otlp_endpoint is None:
        raise ConfigurationError(
            "启用 OpenTelemetry 时必须配置 TELEMETRY_OTLP_ENDPOINT",
        )

    exporter = OTLPSpanExporter(
        endpoint=resolved_settings.telemetry_otlp_endpoint,
        insecure=resolved_settings.telemetry_otlp_insecure,
    )
    provider = TracerProvider(
        resource=Resource.create(
            {
                "service.name": resolved_settings.telemetry_service_name,
                "deployment.environment.name": resolved_settings.app_env,
            },
        ),
        sampler=ParentBased(
            TraceIdRatioBased(
                resolved_settings.telemetry_sample_ratio,
            ),
        ),
        # 生命周期由 FastAPI 显式关闭，避免 atexit 重复清理。
        shutdown_on_exit=False,
    )
    provider.add_span_processor(
        BatchSpanProcessor(exporter),
    )
    _tracer_provider = provider


def shutdown_telemetry() -> None:
    """刷新并关闭 Trace Provider；未启用时安全空操作。"""

    global _tracer_provider

    provider = _tracer_provider
    _tracer_provider = None
    if provider is not None:
        provider.shutdown()


def get_tracer(name: str) -> Tracer:
    """返回项目 Provider 的 Tracer；关闭遥测时返回标准 NoOp Tracer。"""

    if _tracer_provider is None:
        return trace.get_tracer(name)
    return _tracer_provider.get_tracer(name)


@dataclass(slots=True)
class SpanObservation:
    """允许在操作结束时补充计数、状态和耗时。"""

    span: Span

    def add_fields(self, **fields: Any) -> None:
        """以统一脱敏规则写入 Span 属性。"""

        self.span.set_attributes(
            _safe_span_attributes(fields),
        )


@contextmanager
def trace_operation(
    name: str,
    **fields: Any,
) -> Iterator[SpanObservation]:
    """创建当前操作 Span，错误只记录类型，不记录可能敏感的异常消息。"""

    request_id = get_request_id()
    initial_fields = {
        **fields,
        "request_id": request_id,
    }
    tracer = get_tracer("fashion_agent")
    with tracer.start_as_current_span(
        name,
        record_exception=False,
        set_status_on_exception=False,
        attributes=_safe_span_attributes(initial_fields),
    ) as span:
        observation = SpanObservation(span=span)
        try:
            yield observation
        except Exception as exc:
            span.set_attribute(
                "error.type",
                type(exc).__name__,
            )
            span.set_status(Status(StatusCode.ERROR))
            raise
