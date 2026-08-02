"""短期对话窗口测试。"""

import pytest
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    ToolMessage,
)

from app.memory.short_term.conversation_window import (
    build_conversation_window,
)


def test_window_keeps_current_turn_and_recent_complete_turn() -> None:
    """验证轮次数量限制只移除最旧的完整轮次。"""

    messages = (
        HumanMessage(content="第一轮"),
        AIMessage(content="第一轮回复"),
        HumanMessage(content="第二轮"),
        AIMessage(content="第二轮回复"),
        HumanMessage(content="第三轮"),
    )

    window = build_conversation_window(
        messages,
        max_turns=2,
        max_chars=10_000,
    )

    assert [message.content for message in window.messages] == [
        "第二轮",
        "第二轮回复",
        "第三轮",
    ]
    assert window.diagnostics.input_turns == 3
    assert window.diagnostics.selected_turns == 2
    assert window.diagnostics.omitted_messages == 2


def test_window_never_splits_current_tool_call_chain() -> None:
    """验证当前轮超过字符预算时仍完整保留工具调用和结果。"""

    messages = (
        HumanMessage(content="查询我的衣橱"),
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "search_wardrobe",
                    "args": {"category": "衬衫"},
                    "id": "call-001",
                    "type": "tool_call",
                },
            ],
        ),
        ToolMessage(
            content="衣橱结果" * 100,
            tool_call_id="call-001",
            name="search_wardrobe",
        ),
    )

    window = build_conversation_window(
        messages,
        max_turns=1,
        max_chars=20,
    )

    assert window.messages == messages
    assert window.diagnostics.current_turn_exceeds_budget is True


def test_window_does_not_skip_oversized_recent_history() -> None:
    """验证较新历史轮超限后不会跳过它去选择更早内容。"""

    messages = (
        HumanMessage(content="很短的第一轮"),
        AIMessage(content="短回复"),
        HumanMessage(content="第二轮" * 100),
        AIMessage(content="很长的回复" * 100),
        HumanMessage(content="当前轮"),
    )

    window = build_conversation_window(
        messages,
        max_turns=3,
        max_chars=500,
    )

    assert [message.content for message in window.messages] == [
        "当前轮",
    ]
    assert window.diagnostics.omitted_turns == 2


@pytest.mark.parametrize(
    ("max_turns", "max_chars", "message"),
    (
        (0, 100, "max_turns"),
        (1, 0, "max_chars"),
    ),
)
def test_window_rejects_non_positive_limits(
    max_turns: int,
    max_chars: int,
    message: str,
) -> None:
    """验证窗口限制必须是正数。"""

    with pytest.raises(ValueError, match=message):
        build_conversation_window(
            (),
            max_turns=max_turns,
            max_chars=max_chars,
        )
