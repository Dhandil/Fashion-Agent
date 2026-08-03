"""短期会话 State 消息压缩测试。"""

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.memory.short_term.state_compaction import (
    build_omitted_message_removals,
)


def test_build_removals_uses_only_omitted_message_ids() -> None:
    """验证只删除已经进入摘要的消息，不触碰当前窗口。"""

    messages = (
        HumanMessage(content="旧问题", id="human-old"),
        AIMessage(content="旧回答", id="ai-old"),
        HumanMessage(content="当前问题", id="human-current"),
    )

    removals = build_omitted_message_removals(
        messages,
        omitted_message_count=2,
    )

    assert [removal.id for removal in removals] == [
        "human-old",
        "ai-old",
    ]


def test_build_removals_skips_messages_without_ids() -> None:
    """验证直接节点测试中的无 ID 消息不会生成无效删除指令。"""

    removals = build_omitted_message_removals(
        (HumanMessage(content="测试消息"),),
        omitted_message_count=1,
    )

    assert removals == []


def test_build_removals_rejects_negative_count() -> None:
    """验证压缩数量不能为负数。"""

    with pytest.raises(ValueError, match="不能小于 0"):
        build_omitted_message_removals(
            (HumanMessage(content="测试"),),
            omitted_message_count=-1,
        )


def test_build_removals_rejects_invalid_count() -> None:
    """验证删除范围不能超过当前消息列表。"""

    with pytest.raises(ValueError, match="不能超过消息总数"):
        build_omitted_message_removals(
            (),
            omitted_message_count=1,
        )
