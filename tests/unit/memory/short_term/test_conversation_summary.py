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
    """验证同一历史前缀不会在多次聊天调用中重复摘要。"""

    messages = (
        HumanMessage(content="第一轮"),
        AIMessage(content="第一轮回复"),
        HumanMessage(content="第二轮"),
        AIMessage(content="第二轮回复"),
        HumanMessage(content="当前轮"),
    )
    first_summary = update_conversation_summary(
        existing=None,
        messages=messages,
        omitted_message_count=2,
    )
    second_summary = update_conversation_summary(
        existing=first_summary,
        messages=messages,
        omitted_message_count=4,
    )

    assert second_summary is not None
    assert second_summary.covered_message_count == 4
    assert second_summary.content.count("用户：第一轮") == 1
    assert second_summary.content.count("用户：第二轮") == 1


def test_summary_resets_when_message_history_is_replaced() -> None:
    """验证旧会话摘要不会进入一个更短的新消息历史。"""

    existing = ConversationSummary(
        content="用户：旧会话敏感内容",
        covered_message_count=4,
    )
    messages = (
        HumanMessage(content="新会话第一轮"),
        AIMessage(content="新回复"),
        HumanMessage(content="当前轮"),
    )

    summary = update_conversation_summary(
        existing=existing,
        messages=messages,
        omitted_message_count=2,
    )

    assert summary is not None
    assert "旧会话敏感内容" not in summary.content
    assert "新会话第一轮" in summary.content


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
