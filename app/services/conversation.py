"""短期会话生命周期应用服务。"""

import logging

from langgraph.checkpoint.redis.aio import AsyncRedisSaver

from app.core.config import get_settings
from app.core.observability import anonymize_identifier, log_event
from app.memory.short_term.checkpointer import (
    get_short_term_checkpointer,
)
from app.memory.short_term.thread import (
    build_conversation_thread_id,
)

logger = logging.getLogger(__name__)


async def prune_conversation_checkpoints(
    *,
    user_id: str,
    conversation_id: str,
) -> bool:
    """尽力裁剪 Redis 中的旧快照，不让维护失败破坏已经生成的回复。

    Redis Checkpointer 按 Checkpoint Namespace 分别保留最近快照。内存后端用于
    本地开发和测试，不支持持久化裁剪，因此直接返回 ``False``。
    """

    checkpointer = get_short_term_checkpointer()
    if not isinstance(checkpointer, AsyncRedisSaver):
        return False

    thread_id = build_conversation_thread_id(
        user_id=user_id,
        conversation_id=conversation_id,
    )
    keep_last = get_settings().redis_checkpoint_keep_last
    anonymous_user_id = anonymize_identifier(user_id)
    anonymous_conversation_id = anonymize_identifier(
        conversation_id,
    )

    try:
        await checkpointer.aprune(
            [thread_id],
            keep_last=keep_last,
        )
    except Exception as exc:  # noqa: BLE001 - 后台容量维护不能覆盖已成功的业务结果
        # 回复已经生成时，维护任务失败只能记录告警，不能把成功请求改成 500。
        log_event(
            logger,
            "agent.conversation.checkpoints_prune_failed",
            level=logging.WARNING,
            error_type=type(exc).__name__,
            anonymous_user_id=anonymous_user_id,
            anonymous_conversation_id=(anonymous_conversation_id),
        )
        return False

    log_event(
        logger,
        "agent.conversation.checkpoints_pruned",
        keep_last=keep_last,
        anonymous_user_id=anonymous_user_id,
        anonymous_conversation_id=anonymous_conversation_id,
    )
    return True


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
