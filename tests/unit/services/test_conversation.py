"""短期会话生命周期服务测试。"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.redis.aio import AsyncRedisSaver

from app.core.config import Settings
from app.services.conversation import (
    delete_conversation_state,
    prune_conversation_checkpoints,
)


@pytest.mark.anyio
async def test_prune_conversation_keeps_configured_recent_checkpoints() -> None:
    """验证 Redis 按用户会话线程和配置数量裁剪旧快照。"""

    checkpointer = Mock(spec=AsyncRedisSaver)
    settings = Settings(
        _env_file=None,
        short_term_memory_backend="redis",
        redis_url="redis://localhost:6379/0",
        redis_checkpoint_keep_last=25,
    )

    with (
        patch(
            "app.services.conversation.get_short_term_checkpointer",
            return_value=checkpointer,
        ),
        patch(
            "app.services.conversation.get_settings",
            return_value=settings,
        ),
    ):
        was_pruned = await prune_conversation_checkpoints(
            user_id="user-001",
            conversation_id="conversation-001",
        )

    assert was_pruned is True
    checkpointer.aprune.assert_awaited_once_with(
        ["user:user-001:conversation:conversation-001"],
        keep_last=25,
    )


@pytest.mark.anyio
async def test_prune_conversation_is_noop_for_memory_backend() -> None:
    """验证本地内存后端不执行 Redis 专属维护操作。"""

    with patch(
        "app.services.conversation.get_short_term_checkpointer",
        return_value=InMemorySaver(),
    ):
        was_pruned = await prune_conversation_checkpoints(
            user_id="user-001",
            conversation_id="conversation-001",
        )

    assert was_pruned is False


@pytest.mark.anyio
async def test_prune_failure_does_not_break_successful_conversation() -> None:
    """验证容量维护失败只产生告警，不覆盖已经成功的 Agent 回复。"""

    checkpointer = Mock(spec=AsyncRedisSaver)
    checkpointer.aprune.side_effect = RuntimeError("测试维护失败")
    settings = Settings(
        _env_file=None,
        short_term_memory_backend="redis",
        redis_url="redis://localhost:6379/0",
    )

    with (
        patch(
            "app.services.conversation.get_short_term_checkpointer",
            return_value=checkpointer,
        ),
        patch(
            "app.services.conversation.get_settings",
            return_value=settings,
        ),
        patch(
            "app.services.conversation.log_event",
        ) as mocked_log_event,
    ):
        was_pruned = await prune_conversation_checkpoints(
            user_id="user-001",
            conversation_id="conversation-001",
        )

    assert was_pruned is False
    failure_event = mocked_log_event.call_args
    assert failure_event.args[1] == ("agent.conversation.checkpoints_prune_failed")
    assert failure_event.kwargs["error_type"] == "RuntimeError"
    assert "user_id" not in failure_event.kwargs
    assert "conversation_id" not in failure_event.kwargs


@pytest.mark.anyio
async def test_delete_conversation_uses_user_scoped_thread() -> None:
    """验证删除会话时不能遗漏用户隔离前缀。"""

    checkpointer = Mock(spec=BaseCheckpointSaver)
    checkpointer.adelete_thread = AsyncMock()

    with patch(
        "app.services.conversation.get_short_term_checkpointer",
        return_value=checkpointer,
    ):
        await delete_conversation_state(
            user_id="user-001",
            conversation_id="conversation-001",
        )

    checkpointer.adelete_thread.assert_awaited_once_with(
        "user:user-001:conversation:conversation-001",
    )
