"""发送给模型前的短期对话窗口治理。"""

from dataclasses import dataclass

from langchain_core.messages import AnyMessage, HumanMessage

DEFAULT_HISTORY_MAX_TURNS = 6
DEFAULT_HISTORY_MAX_CHARS = 8_000


@dataclass(frozen=True, slots=True)
class ConversationWindowDiagnostics:
    """不包含消息正文的对话窗口诊断信息。"""

    max_turns: int
    max_chars: int
    input_turns: int
    input_messages: int
    input_chars: int
    selected_turns: int
    selected_messages: int
    selected_chars: int
    omitted_turns: int
    omitted_messages: int
    current_turn_exceeds_budget: bool


@dataclass(frozen=True, slots=True)
class ConversationWindow:
    """保留当前轮和最近若干完整历史轮次的模型输入。"""

    messages: tuple[AnyMessage, ...]
    diagnostics: ConversationWindowDiagnostics


def _message_chars(message: AnyMessage) -> int:
    """估算消息的序列化字符数，并包含工具调用参数。"""

    return len(
        message.model_dump_json(
            exclude={"response_metadata"},
        ),
    )


def _split_complete_turns(
    messages: tuple[AnyMessage, ...],
) -> tuple[tuple[AnyMessage, ...], ...]:
    """以用户消息为边界切分对话，同时保持工具调用链完整。"""

    if not messages:
        return ()

    turns: list[list[AnyMessage]] = []
    leading_messages: list[AnyMessage] = []
    current_turn: list[AnyMessage] = []

    for message in messages:
        if isinstance(message, HumanMessage):
            if current_turn:
                turns.append(current_turn)
            current_turn = [message]
        elif current_turn:
            current_turn.append(message)
        else:
            leading_messages.append(message)

    if current_turn:
        turns.append(current_turn)
    elif leading_messages:
        return (tuple(leading_messages),)

    if leading_messages:
        turns[0] = [*leading_messages, *turns[0]]

    return tuple(tuple(turn) for turn in turns)


def build_conversation_window(
    messages: tuple[AnyMessage, ...],
    *,
    max_turns: int = DEFAULT_HISTORY_MAX_TURNS,
    max_chars: int = DEFAULT_HISTORY_MAX_CHARS,
) -> ConversationWindow:
    """保留当前完整轮次，并在预算内加入连续的最近历史轮次。"""

    if max_turns <= 0:
        raise ValueError("max_turns 必须大于 0")
    if max_chars <= 0:
        raise ValueError("max_chars 必须大于 0")

    turns = _split_complete_turns(messages)
    turn_chars = tuple(sum(_message_chars(message) for message in turn) for turn in turns)
    input_chars = sum(turn_chars)

    if not turns:
        return ConversationWindow(
            messages=(),
            diagnostics=ConversationWindowDiagnostics(
                max_turns=max_turns,
                max_chars=max_chars,
                input_turns=0,
                input_messages=0,
                input_chars=0,
                selected_turns=0,
                selected_messages=0,
                selected_chars=0,
                omitted_turns=0,
                omitted_messages=0,
                current_turn_exceeds_budget=False,
            ),
        )

    # 当前轮可能包含尚未完成的工具调用链，必须整体保留，不能按字符截断。
    first_selected_index = len(turns) - 1
    selected_chars = turn_chars[-1]

    for index in range(len(turns) - 2, -1, -1):
        if len(turns) - first_selected_index >= max_turns:
            break
        if selected_chars + turn_chars[index] > max_chars:
            # 保持时间窗口连续；不跨过超长的较新轮次选择更早内容。
            break
        first_selected_index = index
        selected_chars += turn_chars[index]

    selected_turns = turns[first_selected_index:]
    selected_messages = tuple(message for turn in selected_turns for message in turn)
    omitted_turns = turns[:first_selected_index]
    omitted_message_count = sum(len(turn) for turn in omitted_turns)

    return ConversationWindow(
        messages=selected_messages,
        diagnostics=ConversationWindowDiagnostics(
            max_turns=max_turns,
            max_chars=max_chars,
            input_turns=len(turns),
            input_messages=len(messages),
            input_chars=input_chars,
            selected_turns=len(selected_turns),
            selected_messages=len(selected_messages),
            selected_chars=selected_chars,
            omitted_turns=len(omitted_turns),
            omitted_messages=omitted_message_count,
            current_turn_exceeds_budget=(turn_chars[-1] > max_chars),
        ),
    )
