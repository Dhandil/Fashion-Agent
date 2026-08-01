"""HTTP request_id 中间件集成测试。"""

from uuid import UUID

from fastapi.testclient import TestClient

from app.main import create_app

client = TestClient(create_app())


def test_request_id_middleware_reuses_safe_client_id() -> None:
    """验证合法的客户端 request_id 会在响应头中原样返回。"""

    response = client.get(
        "/api/v1/health",
        headers={
            "X-Request-ID": "frontend-request-001",
        },
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == ("frontend-request-001")


def test_request_id_middleware_replaces_unsafe_client_id() -> None:
    """验证含非法字符的追踪 ID 不会进入日志链路。"""

    response = client.get(
        "/api/v1/health",
        headers={
            "X-Request-ID": "unsafe request id",
        },
    )

    assert response.status_code == 200
    generated_request_id = response.headers["X-Request-ID"]
    assert generated_request_id != "unsafe request id"
    assert UUID(generated_request_id)
