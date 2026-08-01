"""不依赖外部平台的结构化链路事件。"""

import json
import logging
from typing import Any

from app.core.request_context import get_request_id


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
