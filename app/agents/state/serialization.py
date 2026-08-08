"""Agent State 中可持久化模型的兼容转换工具。"""

import json
from datetime import date, datetime
from enum import Enum
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

ModelT = TypeVar("ModelT", bound=BaseModel)


def model_to_json(value: Any) -> str:
    """把 Pydantic 模型或 Redis 恢复后的字典转换为 JSON 文本。

    LangGraph 的不同 Checkpointer 实现可能返回 Pydantic 对象，也可能返回
    已经反序列化的普通字典。上下文渲染只需要稳定 JSON，不应该依赖某一种
    Checkpointer 的具体返回类型。
    """

    if isinstance(value, BaseModel):
        return value.model_dump_json()

    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        default=_json_default,
    )


def coerce_model(value: Any, model_type: type[ModelT]) -> ModelT | None:
    """将恢复状态中的字典转换回指定模型；空值保持为空。"""

    if value is None:
        return None
    if isinstance(value, model_type):
        return value
    try:
        return model_type.model_validate(value)
    except ValidationError:
        # 历史 Checkpoint 可能包含旧版本或不完整的派生状态。
        # 这类数据不是权威事实，丢弃它比阻塞当前对话更安全。
        return None


def _json_default(value: Any) -> Any:
    """处理普通字典中可能出现的枚举和日期值。"""

    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    return str(value)
