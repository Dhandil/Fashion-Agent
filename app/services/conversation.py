"""短期会话生命周期应用服务。"""

from app.memory.short_term.checkpointer import (
    get_short_term_checkpointer,
)
from app.memory.short_term.thread import (
    build_conversation_thread_id,
)


async def delete_conversation_state(
    *,
    user_id: str,
    conversation_id: str,
) -> None:
    """幂等删除当前用户的一条 LangGraph 会话状态。"""

    thread_id = build_conversation_thread_id(
        user_id=user_id,
        conversation_id=conversation_id,
    )
    await get_short_term_checkpointer().adelete_thread(thread_id)
