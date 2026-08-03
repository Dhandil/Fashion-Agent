"""不调用模型的提取式滚动对话摘要。"""

from collections.abc import Sequence
from typing import Self

from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    HumanMessage,
)
from pydantic import BaseModel, ConfigDict, Field, model_validator

DEFAULT_SUMMARY_MAX_CHARS = 2_000
_TRUNCATION_MARKER = "[较早的对话摘要已按预算省略]"


class ConversationSummary(BaseModel):
    """随 Checkpointer 保存、但不作为动态事实依据的摘要。"""

    content: str
    covered_message_count: int = Field(ge=0)

    model_config = ConfigDict(frozen=True)

    @model_validator(mode="after")
    def validate_non_empty_progress(self) -> Self:
        """没有覆盖消息时不应保存摘要正文。"""

        if self.covered_message_count == 0 and self.content:
            raise ValueError(
                "未覆盖任何消息时不能包含摘要正文",
            )
        return self


def _normalise_text(content: str) -> str:
    """把多行消息压成稳定单行，避免复制完整消息格式。"""

    return " ".join(content.split())


def _extract_summary_lines(
    messages: Sequence[AnyMessage],
) -> list[str]:
    """只提取人机文本，明确排除 ToolMessage 和空工具调用回复。"""

    lines: list[str] = []
    for message in messages:
        if isinstance(message, HumanMessage):
            role = "用户"
        elif isinstance(message, AIMessage):
            role = "助手"
        else:
            continue

        if not isinstance(message.content, str):
            continue
        content = _normalise_text(message.content)
        if content:
            lines.append(f"{role}：{content}")
    return lines


def _fit_recent_lines(
    lines: list[str],
    max_chars: int,
) -> str:
    """在字符预算内保留最近的完整摘要行。"""

    if max_chars <= len(_TRUNCATION_MARKER) + 10:
        raise ValueError("max_chars 太小，无法安全保存摘要")
    if not lines:
        return ""

    # 旧摘要可能已经带有截断标记，重新计算时只保留一个。
    clean_lines = [line for line in lines if line != _TRUNCATION_MARKER]
    selected_reversed: list[str] = []
    used_chars = 0

    for line in reversed(clean_lines):
        separator_chars = 1 if selected_reversed else 0
        if used_chars + separator_chars + len(line) > max_chars:
            break
        selected_reversed.append(line)
        used_chars += separator_chars + len(line)

    was_truncated = len(selected_reversed) < len(clean_lines)
    if not was_truncated:
        return "\n".join(reversed(selected_reversed))

    marker_chars = len(_TRUNCATION_MARKER) + 1
    while selected_reversed and used_chars + marker_chars > max_chars:
        removed_line = selected_reversed.pop()
        used_chars -= len(removed_line)
        if selected_reversed:
            used_chars -= 1

    if not selected_reversed:
        available_chars = max_chars - marker_chars
        newest_line = clean_lines[-1]
        selected_reversed.append(
            newest_line[:available_chars].rstrip(),
        )

    return "\n".join(
        (
            _TRUNCATION_MARKER,
            *reversed(selected_reversed),
        ),
    )


def update_conversation_summary(
    *,
    existing: ConversationSummary | None,
    messages: tuple[AnyMessage, ...],
    omitted_message_count: int,
    max_chars: int = DEFAULT_SUMMARY_MAX_CHARS,
) -> ConversationSummary | None:
    """把本次退出对话窗口的消息增量合并进提取式摘要。

    调用方会在摘要生成后从 LangGraph State 中移除这批旧消息，因此传入的
    ``messages`` 都视为尚未摘要的当前状态。``covered_message_count`` 记录
    会话生命周期内累计压缩的消息数，不再作为当前消息列表的切片下标。
    """

    if omitted_message_count < 0:
        raise ValueError("omitted_message_count 不能小于 0")
    if omitted_message_count > len(messages):
        raise ValueError(
            "omitted_message_count 不能超过消息总数",
        )

    existing_content = existing.content if existing is not None else ""
    if omitted_message_count == 0:
        return existing

    new_lines = _extract_summary_lines(
        messages[:omitted_message_count],
    )
    all_lines = [
        *existing_content.splitlines(),
        *new_lines,
    ]
    content = _fit_recent_lines(
        all_lines,
        max_chars=max_chars,
    )
    return ConversationSummary(
        content=content,
        covered_message_count=(
            (existing.covered_message_count if existing is not None else 0) + omitted_message_count
        ),
    )
