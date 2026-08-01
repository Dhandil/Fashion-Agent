"""HTTP request_id 生成、传播与基础请求事件。"""

import logging
import re
from collections.abc import Awaitable, Callable
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request, Response

from app.core.observability import log_event
from app.core.request_context import (
    reset_request_id,
    set_request_id,
)

logger = logging.getLogger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"
_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,100}$")


def _resolve_request_id(header_value: str | None) -> str:
    """复用合法客户端 ID，否则生成新的 UUID。"""

    if header_value is not None and _SAFE_REQUEST_ID.fullmatch(header_value):
        return header_value
    return str(uuid4())


async def request_id_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """为单次 HTTP 请求设置追踪上下文并返回响应头。"""

    request_id = _resolve_request_id(
        request.headers.get(REQUEST_ID_HEADER),
    )
    token = set_request_id(request_id)
    started_at = perf_counter()
    log_event(
        logger,
        "http.request.started",
        method=request.method,
        path=request.url.path,
    )

    try:
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        log_event(
            logger,
            "http.request.completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(
                (perf_counter() - started_at) * 1000,
                2,
            ),
        )
        return response
    except Exception as exc:
        log_event(
            logger,
            "http.request.failed",
            level=logging.ERROR,
            method=request.method,
            path=request.url.path,
            error_type=type(exc).__name__,
            duration_ms=round(
                (perf_counter() - started_at) * 1000,
                2,
            ),
        )
        raise
    finally:
        reset_request_id(token)


def register_request_id_middleware(
    application: FastAPI,
) -> None:
    """在应用创建阶段注册 request_id 中间件。"""

    application.middleware("http")(
        request_id_middleware,
    )
