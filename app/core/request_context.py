"""请求级追踪上下文。"""

from contextvars import ContextVar, Token

_request_id: ContextVar[str | None] = ContextVar(
    "request_id",
    default=None,
)


def get_request_id() -> str | None:
    """取得当前异步请求的追踪 ID。"""

    return _request_id.get()


def set_request_id(request_id: str) -> Token[str | None]:
    """写入当前请求 ID，并返回用于恢复上下文的令牌。"""

    return _request_id.set(request_id)


def reset_request_id(token: Token[str | None]) -> None:
    """请求结束时恢复进入请求前的上下文。"""

    _request_id.reset(token)
