"""请求级追踪上下文测试。"""

from app.core.request_context import (
    get_request_id,
    reset_request_id,
    set_request_id,
)


def test_request_id_can_be_set_and_reset() -> None:
    """验证请求结束后不会把 request_id 泄漏给下一次请求。"""

    assert get_request_id() is None

    token = set_request_id("request-001")
    assert get_request_id() == "request-001"

    reset_request_id(token)
    assert get_request_id() is None
