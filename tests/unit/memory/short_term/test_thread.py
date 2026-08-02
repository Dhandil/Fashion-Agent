"""短期会话线程键测试。"""

from app.memory.short_term.thread import (
    build_conversation_thread_id,
)


def test_thread_id_is_scoped_by_user_and_conversation() -> None:
    """验证用户身份和会话 ID 都进入稳定线程键。"""

    assert build_conversation_thread_id(
        user_id="user-001",
        conversation_id="conversation-001",
    ) == "user:user-001:conversation:conversation-001"

    assert build_conversation_thread_id(
        user_id="user-002",
        conversation_id="conversation-001",
    ) != build_conversation_thread_id(
        user_id="user-001",
        conversation_id="conversation-001",
    )
