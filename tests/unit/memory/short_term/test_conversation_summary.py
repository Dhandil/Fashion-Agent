"""提取式滚动对话摘要测试。"""

import pytest
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    ToolMessage,
)

from app.memory.short_term.conversation_summary import (
    ConversationSummary,
    update_conversation_summary,
)


def test_summary_extracts_human_and_ai_text_only() -> None:
    """验证摘要不复制工具结果或空工具调用回复。"""

    messages = (
        HumanMessage(content="我想搭配通勤服装"),
        AIMessage(content="我先查询你的衣橱"),
        ToolMessage(
            content='[{"name":"隐私衣物数据"}]',
            tool_call_id="call-001",
            name="search_wardrobe",
        ),
        AIMessage(content=""),
    )

    summary = update_conversation_summary(
        existing=None,
        messages=messages,
        omitted_message_count=4,
    )

    assert summary is not None
    assert "用户：我想搭配通勤服装" in summary.content
    assert "助手：我先查询你的衣橱" in summary.content
    assert "隐私衣物数据" not in summary.content


def test_summary_incrementally_adds_only_newly_omitted_messages() -> None:
    """验证 State 压缩后新退出窗口的消息会继续累加到摘要。"""

    first_messages = (
        HumanMessage(content="第一轮"),
        AIMessage(content="第一轮回复"),
        HumanMessage(content="当前轮"),
    )
    second_messages = (
        HumanMessage(content="第二轮"),
        AIMessage(content="第二轮回复"),
        HumanMessage(content="当前轮"),
    )
    first_summary = update_conversation_summary(
        existing=None,
        messages=first_messages,
        omitted_message_count=2,
    )
    second_summary = update_conversation_summary(
        existing=first_summary,
        messages=second_messages,
        omitted_message_count=2,
    )

    assert second_summary is not None
    assert second_summary.covered_message_count == 4
    assert second_summary.content.count("用户：第一轮") == 1
    assert second_summary.content.count("用户：第二轮") == 1


def test_summary_is_unchanged_when_no_message_leaves_window() -> None:
    """验证当前 State 没有消息退出窗口时不会重复写入摘要。"""

    existing = ConversationSummary(
        content="用户：旧会话敏感内容",
        covered_message_count=4,
    )
    summary = update_conversation_summary(
        existing=existing,
        messages=(HumanMessage(content="当前轮"),),
        omitted_message_count=0,
    )

    assert summary is existing


def test_summary_keeps_recent_content_within_budget() -> None:
    """验证摘要超限时优先保留较新的对话内容。"""

    messages = tuple(HumanMessage(content=f"第{index}轮" + "内容" * 20) for index in range(6))

    summary = update_conversation_summary(
        existing=None,
        messages=messages,
        omitted_message_count=len(messages),
        max_chars=100,
    )

    assert summary is not None
    assert len(summary.content) <= 100
    assert "较早的对话摘要已按预算省略" in summary.content
    assert "第5轮" in summary.content


def test_summary_rejects_invalid_omitted_count() -> None:
    """验证摘要覆盖范围不能超出当前消息历史。"""

    with pytest.raises(ValueError, match="不能超过消息总数"):
        update_conversation_summary(
            existing=None,
            messages=(),
            omitted_message_count=1,
        )


def test_summary_covered_count_accumulates_independently_of_message_list() -> None:
    """验证摘要累计计数不受 State 压缩影响（消息已从 State 删除后计数仍正确）。

    新的实现中 ``covered_message_count`` 是生命周期内累计压缩消息数，不再作为
    当前消息列表的切片下标。本测试模拟三轮压缩，验证每轮累加值一致。
    """

    # 第一轮：6 条消息中前 2 条退出窗口
    round1 = update_conversation_summary(
        existing=None,
        messages=tuple(
            HumanMessage(content=f"第1轮-消息{idx}") for idx in range(6)
        ),
        omitted_message_count=2,
    )
    assert round1 is not None
    assert round1.covered_message_count == 2

    # 第二轮：State 压缩后只剩 4 条消息（新 + 保留），前 2 条再次退出
    round2 = update_conversation_summary(
        existing=round1,
        messages=tuple(
            HumanMessage(content=f"第2轮-消息{idx}") for idx in range(4)
        ),
        omitted_message_count=2,
    )
    assert round2 is not None
    assert round2.covered_message_count == 4  # 累计 2 + 2

    # 第三轮：消息窗口持续缩小，新退出窗口的消息继续累加
    round3 = update_conversation_summary(
        existing=round2,
        messages=tuple(
            HumanMessage(content=f"第3轮-消息{idx}") for idx in range(2)
        ),
        omitted_message_count=1,
    )
    assert round3 is not None
    assert round3.covered_message_count == 5  # 累计 2 + 2 + 1
    # 三轮摘要内容均存在（没有因为计数错误而重置）
    assert "第1轮" in round3.content
    assert "第2轮" in round3.content
    assert "第3轮" in round3.content
