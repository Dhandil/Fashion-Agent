"""短期会话生命周期服务测试。"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from langgraph.checkpoint.base import BaseCheckpointSaver

from app.services.conversation import delete_conversation_state


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
