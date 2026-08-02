"""不依赖外部平台的结构化链路事件。"""

import json
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from hashlib import sha256
from hmac import new as new_hmac
from secrets import token_bytes
from time import perf_counter
from typing import Any

from app.core.request_context import get_request_id

_ANONYMIZATION_KEY = token_bytes(32)


def anonymize_identifier(value: str) -> str:
    """生成仅在当前进程内稳定的不可逆关联标识。"""

    return new_hmac(
        _ANONYMIZATION_KEY,
        value.encode("utf-8"),
        sha256,
    ).hexdigest()[:16]


@dataclass(slots=True)
class OperationObservation:
    """一次操作在结束前可以补充的非敏感观测字段。"""

    fields: dict[str, Any] = field(
        default_factory=dict,
    )

    def add_fields(self, **fields: Any) -> None:
        """追加结果数量、状态等结束时才知道的字段。"""

        self.fields.update(fields)


def log_event(
    logger: logging.Logger,
    event: str,
    *,
    level: int = logging.INFO,
    **fields: Any,
) -> None:
    """把事件写成单行 JSON，并自动关联当前 request_id。"""

    payload = {
        "event": event,
        "request_id": get_request_id(),
        **fields,
    }
    logger.log(
        level,
        json.dumps(
            payload,
            ensure_ascii=False,
            default=str,
            sort_keys=True,
        ),
    )


@contextmanager
def observe_operation(
    logger: logging.Logger,
    event: str,
    **fields: Any,
) -> Iterator[OperationObservation]:
    """记录同步或异步代码块的耗时与失败类型。"""

    started_at = perf_counter()
    observation = OperationObservation()
    try:
        yield observation
    except Exception as exc:
        failure_fields = {
            **fields,
            **observation.fields,
            "error_type": type(exc).__name__,
            "duration_ms": round(
                (perf_counter() - started_at) * 1000,
                2,
            ),
        }
        log_event(
            logger,
            f"{event}.failed",
            level=logging.ERROR,
            **failure_fields,
        )
        raise
    else:
        completion_fields = {
            **fields,
            **observation.fields,
            "duration_ms": round(
                (perf_counter() - started_at) * 1000,
                2,
            ),
        }
        log_event(
            logger,
            f"{event}.completed",
            **completion_fields,
        )
