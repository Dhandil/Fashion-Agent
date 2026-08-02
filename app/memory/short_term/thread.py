"""短期会话在 LangGraph Checkpointer 中的稳定键规则。"""


def build_conversation_thread_id(
    *,
    user_id: str,
    conversation_id: str,
) -> str:
    """组合用户和会话 ID，保证不同用户不能共享状态。"""

    return f"user:{user_id}:conversation:{conversation_id}"
