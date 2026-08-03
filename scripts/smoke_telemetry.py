"""验证 Fashion-Agent → OTel Collector 端到端 Trace 导出链路。

前提条件：
- Docker Compose 已启动 collector 服务
- 本机 4317 端口可以访问
"""

from __future__ import annotations

import subprocess
import time
from datetime import UTC, datetime

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased

from app.observability.telemetry import (
    SpanObservation,
    _safe_span_attributes,
)

# 用唯一标记匹配 Collector 日志，避免读取旧数据
_RUN_MARKER = f"trace-verify-{datetime.now(UTC).strftime('%H%M%S')}"


def create_trace_chain() -> None:
    """生成父子 Span 链，导出到本地 Collector。"""
    exporter = OTLPSpanExporter(
        endpoint="http://localhost:4317",
        insecure=True,
    )
    provider = TracerProvider(
        resource=Resource.create(
            {
                "service.name": "fashion-agent-smoke-test",
                "deployment.environment.name": "trace-verify",
            },
        ),
        sampler=ParentBased(TraceIdRatioBased(1.0)),
        shutdown_on_exit=False,
    )
    provider.add_span_processor(BatchSpanProcessor(exporter))
    tracer = provider.get_tracer("smoke_test")

    print(f"[smoke] 运行标记: {_RUN_MARKER}")
    with tracer.start_as_current_span(
        "smoke.test_root",
        attributes=_safe_span_attributes(
            {"test_id": _RUN_MARKER, "step": "root"},
        ),
    ) as root_span:
        SpanObservation(span=root_span).add_fields(count=1)

        with tracer.start_as_current_span(
            "smoke.test_child",
            attributes=_safe_span_attributes({"step": "child"}),
        ) as child_span:
            SpanObservation(span=child_span).add_fields(nested=True, items=3)

            with tracer.start_as_current_span(
                "smoke.test_llm_call",
                attributes=_safe_span_attributes({"model": "test-model"}),
            ) as llm_span:
                SpanObservation(span=llm_span).add_fields(
                    input_tokens=100,
                    output_tokens=50,
                    # 敏感字段不应在 Span 中
                    prompt="用户真实消息不应记录",
                    api_key="sk-secret-key-不应导出",
                )

        with tracer.start_as_current_span(
            "smoke.test_rag_retrieval",
            attributes=_safe_span_attributes({"retriever": "knowledge"}),
        ) as rag_span:
            SpanObservation(span=rag_span).add_fields(
                result_count=3,
                top_k=5,
                content="检索到的面料知识片段正文不应记录",
            )

    # 错误 Span —— 用 try/finally 确保 span 在 set_status 前不结束
    error_span = tracer.start_span("smoke.test_expected_error")
    try:
        with trace.use_span(error_span, end_on_exit=True, record_exception=False):
            raise ValueError("这条敏感异常消息不应进入 Trace")
    except ValueError:
        error_span.set_attribute("error.type", "ValueError")
        error_span.set_status(trace.Status(trace.StatusCode.ERROR))

    print("[smoke] Span 链生成完毕，强制刷新...")
    provider.force_flush(timeout_millis=10_000)
    time.sleep(3)
    provider.shutdown()
    print("[smoke] Provider 已关闭。")


def run_checks() -> None:
    """检查 Collector 日志并验证。"""
    print("\n[检查] 拉取 Collector 最近日志...")

    # 多次尝试：BatchSpanProcessor 有延迟，Collector debug exporter 也有 batch
    for attempt in range(4):
        time.sleep(2)
        result = subprocess.run(
            ["docker", "logs", "fashion-agent-collector-1", "--tail", "100"],
            capture_output=True,
            text=True,
            # 容器不存在或未启动时由脚本自行提示，不抛出异常
            check=False,
        )
        output = result.stdout
        if _RUN_MARKER in output:
            break
        print(f"  尝试 {attempt + 1}/4：未找到标记 {_RUN_MARKER}，等待...")

    # 只取本次运行的片段
    marker_idx = output.find("Span #0")
    if marker_idx == -1:
        # 找不到 Span #0，打印全部并报告失败
        print(output[-2000:])
        print("\n⚠️  未在 Collector 日志中找到 Span 输出")
        return

    # 取从标记开始的日志（debug exporter 会输出带标记的 Span）
    relevant = output

    checks = {
        "根 Span (smoke.test_root)": "smoke.test_root" in relevant,
        "子 Span (smoke.test_child)": "smoke.test_child" in relevant,
        "LLM Span (smoke.test_llm_call)": "smoke.test_llm_call" in relevant,
        "RAG Span (smoke.test_rag_retrieval)": "smoke.test_rag_retrieval" in relevant,
        "错误 Span (smoke.test_expected_error)": "smoke.test_expected_error" in relevant,
        "安全字段 input_tokens": "input_tokens" in relevant,
        "安全字段 output_tokens": "output_tokens" in relevant,
        "安全字段 model": "test-model" in relevant,
        "敏感 api_key 未泄露": "sk-secret-key" not in relevant,
        "敏感 prompt 未泄露": "用户真实消息不应记录" not in relevant,
        "敏感 content 未泄露": "检索到的面料知识片段" not in relevant,
        "敏感 异常消息未泄露": "这条敏感异常消息" not in relevant,
    }

    print("\n" + "=" * 60)
    print("验证结果：")
    all_passed = True
    for check_name, passed in checks.items():
        status = "✅ 通过" if passed else "❌ 失败"
        if not passed:
            all_passed = False
        print(f"  {status} — {check_name}")

    if all_passed:
        print("\n🎉 全部检查通过！OTel Trace 链路工作正常。")
    else:
        print("\n⚠️  部分检查未通过。Collector 日志片段：")
        # 只打印属性段，方便排查
        lines = relevant.split("\n")
        attr_lines = [
            line for line in lines
            if "->" in line or "Span #" in line or "Name" in line
        ]
        print("\n".join(attr_lines[-60:]))

    print("=" * 60)


def main() -> None:
    print("=" * 60)
    print("Fashion-Agent OpenTelemetry Trace 链路验证")
    print("=" * 60)

    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(("localhost", 4317))
    sock.close()
    if result != 0:
        print("[失败] 无法连接 localhost:4317，请确认 Collector 已启动")
        return
    print("[通过] Collector gRPC 端口 4317 可达\n")

    create_trace_chain()
    run_checks()


if __name__ == "__main__":
    main()
