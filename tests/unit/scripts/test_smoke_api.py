"""只读 API 冒烟脚本测试。"""

import json

import httpx
import pytest

from scripts.smoke_api import (
    READ_ONLY_CHECKS,
    SmokeCheck,
    SmokeCheckError,
    run_smoke_checks,
    validate_payload,
)


def test_validate_payload_rejects_missing_contract_field() -> None:
    """验证响应缺少最小契约字段时检查失败。"""

    check = SmokeCheck(
        name="测试接口",
        path="/test",
        required_keys=("items", "count"),
    )

    with pytest.raises(
        SmokeCheckError,
        match="count",
    ):
        validate_payload(check, {"items": []})


def test_run_smoke_checks_uses_only_get_and_scopes_user() -> None:
    """验证冒烟检查只读取数据，并为业务接口携带测试身份。"""

    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/api/v1/health":
            payload = {
                "status": "ok",
                "app_name": "Fashion-Agent",
                "environment": "test",
            }
        elif request.url.path == "/api/v1/health/ready":
            payload = {
                "status": "ready",
                "checks": {
                    "database": "ok",
                    "short_term_memory": "memory",
                },
            }
        elif request.url.path == "/api/v1/style-profile":
            payload = {
                "preferred_styles": [],
                "avoided_styles": [],
            }
        else:
            payload = {
                "items": [],
                "count": 0,
                "total": 0,
                "include_expired": False,
            }
        return httpx.Response(
            status_code=200,
            content=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )

    passed = run_smoke_checks(
        base_url="http://testserver",
        user_id="smoke-user",
        timeout=1.0,
        transport=httpx.MockTransport(handler),
    )

    assert len(passed) == len(READ_ONLY_CHECKS)
    assert all(request.method == "GET" for request in requests)
    assert all(
        (
            request.headers["X-User-ID"] == "smoke-user"
            if check.authenticated
            else "X-User-ID" not in request.headers
        )
        for check, request in zip(
            READ_ONLY_CHECKS,
            requests,
            strict=True,
        )
    )


def test_health_payload_requires_ok_status() -> None:
    """验证健康端点只有明确返回 ok 才能通过。"""

    with pytest.raises(SmokeCheckError, match="不是 ok"):
        validate_payload(
            READ_ONLY_CHECKS[0],
            {
                "status": "degraded",
                "app_name": "Fashion-Agent",
                "environment": "test",
            },
        )
