"""短期记忆 Checkpointer 工厂测试。"""

from unittest.mock import Mock, patch

import pytest
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver

from app.core.config import Settings
from app.core.exceptions import ConfigurationError
from app.memory.short_term.checkpointer import (
    create_short_term_checkpointer,
)


def test_create_memory_checkpointer_by_default() -> None:
    """验证本地默认配置继续使用进程内存。"""

    checkpointer = create_short_term_checkpointer(
        Settings(_env_file=None),
    )

    assert isinstance(checkpointer, InMemorySaver)


def test_redis_checkpointer_requires_url() -> None:
    """验证 Redis 后端不能在缺少连接地址时静默降级。"""

    settings = Settings(
        _env_file=None,
        short_term_memory_backend="redis",
    )

    with pytest.raises(
        ConfigurationError,
        match="REDIS_URL",
    ):
        create_short_term_checkpointer(settings)


def test_create_redis_checkpointer_with_refreshing_ttl() -> None:
    """验证 Redis Checkpointer 使用安全连接值和刷新 TTL。"""

    settings = Settings(
        _env_file=None,
        short_term_memory_backend="redis",
        redis_url="redis://:test-secret@localhost:6379/0",
        redis_checkpoint_ttl_minutes=90,
    )
    checkpointer = Mock(spec=BaseCheckpointSaver)

    with patch(
        "app.memory.short_term.checkpointer.AsyncRedisSaver",
        return_value=checkpointer,
    ) as saver_class:
        result = create_short_term_checkpointer(settings)

    assert result is checkpointer
    saver_class.assert_called_once_with(
        redis_url="redis://:test-secret@localhost:6379/0",
        ttl={
            "default_ttl": 90,
            "refresh_on_read": True,
        },
    )
