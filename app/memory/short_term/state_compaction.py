"""LangGraph 短期会话 State 的消息压缩辅助函数。"""

from collections.abc import Sequence

from langchain_core.messages import AnyMessage, RemoveMessage


def build_omitted_message_removals(
    messages: Sequence[AnyMessage],
    *,
    omitted_message_count: int,
) -> list[RemoveMessage]:
    """为已进入滚动摘要的消息生成 LangGraph 删除指令。

    ``add_messages`` Reducer 会根据消息 ID 应用 ``RemoveMessage``。在真实图中
    LangGraph 会为进入 State 的消息补充 ID；直接调用节点的单元测试可能没有
    ID，此时跳过删除指令，避免构造无效操作。
    """

    if omitted_message_count < 0:
        raise ValueError("omitted_message_count 不能小于 0")
    if omitted_message_count > len(messages):
        raise ValueError(
            "omitted_message_count 不能超过消息总数",
        )

    return [
        RemoveMessage(id=message.id)
        for message in messages[:omitted_message_count]
        if message.id is not None
    ]
