"""Agent 当前对话轮次的上下文辅助函数。"""

import json
from collections.abc import Sequence
from typing import Any, cast

from langchain_core.messages import (
    AnyMessage,
    HumanMessage,
    ToolMessage,
)


def get_current_turn_messages(
    messages: Sequence[AnyMessage],
) -> list[AnyMessage]:
    """返回最后一条用户消息及其之后产生的消息。"""

    # 从末尾查找，可以避免上一轮 ToolMessage 影响当前轮路由
    for index in range(
        len(messages) - 1,
        -1,
        -1,
    ):
        if isinstance(
            messages[index],
            HumanMessage,
        ):
            return list(messages[index:])

    # 防御性回退：没有用户消息时返回现有消息快照
    return list(messages)


def get_current_turn_tool_records(
    messages: Sequence[AnyMessage],
    tool_name: str,
) -> tuple[dict[str, Any], ...]:
    """读取当前轮指定工具成功返回的 JSON 对象列表。"""

    records: list[dict[str, Any]] = []

    for message in get_current_turn_messages(messages):
        if (
            not isinstance(message, ToolMessage)
            or message.name != tool_name
            or message.status != "success"
            or not isinstance(message.content, str)
        ):
            continue

        try:
            parsed_content: Any = json.loads(
                message.content,
            )
        except json.JSONDecodeError:
            # 非 JSON 工具结果不能作为结构化 Outfit 的来源证据
            continue

        if not isinstance(parsed_content, list):
            continue

        for record in parsed_content:
            if isinstance(record, dict):
                records.append(
                    cast(
                        dict[str, Any],
                        record,
                    ),
                )

    return tuple(records)
