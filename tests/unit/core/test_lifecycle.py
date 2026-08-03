"""FastAPI 应用生命周期测试。"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import FastAPI

from app.core.lifecycle import application_lifespan


@pytest.mark.anyio
async def test_application_lifespan_closes_database_resources() -> None:
    """验证应用退出时即使没有业务请求也执行统一资源清理。"""

    application = Mock(spec=FastAPI)
    initialize_checkpointer = AsyncMock()
    close_checkpointer = AsyncMock()
    close_connections = AsyncMock()
    initialize_telemetry = Mock()
    shutdown_telemetry = Mock()

    with (
        patch(
            "app.core.lifecycle.initialize_short_term_checkpointer",
            initialize_checkpointer,
        ),
        patch(
            "app.core.lifecycle.close_short_term_checkpointer",
            close_checkpointer,
        ),
        patch(
            "app.core.lifecycle.close_database_connections",
            close_connections,
        ),
        patch(
            "app.core.lifecycle.initialize_telemetry",
            initialize_telemetry,
        ),
        patch(
            "app.core.lifecycle.shutdown_telemetry",
            shutdown_telemetry,
        ),
    ):
        async with application_lifespan(application):
            initialize_telemetry.assert_called_once_with()
            initialize_checkpointer.assert_awaited_once()
            close_checkpointer.assert_not_awaited()
            close_connections.assert_not_awaited()

    close_checkpointer.assert_awaited_once()
    close_connections.assert_awaited_once()
    shutdown_telemetry.assert_called_once_with()


@pytest.mark.anyio
async def test_application_lifespan_closes_database_when_memory_close_fails() -> None:
    """验证短期记忆关闭失败时数据库连接仍会释放。"""

    application = Mock(spec=FastAPI)
    close_connections = AsyncMock()
    shutdown_telemetry = Mock()

    with (
        patch(
            "app.core.lifecycle.initialize_short_term_checkpointer",
            AsyncMock(),
        ),
        patch(
            "app.core.lifecycle.close_short_term_checkpointer",
            AsyncMock(side_effect=RuntimeError("redis close failed")),
        ),
        patch(
            "app.core.lifecycle.close_database_connections",
            close_connections,
        ),
        patch(
            "app.core.lifecycle.initialize_telemetry",
            Mock(),
        ),
        patch(
            "app.core.lifecycle.shutdown_telemetry",
            shutdown_telemetry,
        ),
        pytest.raises(RuntimeError, match="redis close failed"),
    ):
        async with application_lifespan(application):
            pass

    close_connections.assert_awaited_once()
    shutdown_telemetry.assert_called_once_with()


@pytest.mark.anyio
async def test_application_lifespan_closes_telemetry_when_startup_fails() -> None:
    """验证 Redis 初始化失败时已创建的 Trace Provider 仍会关闭。"""

    application = Mock(spec=FastAPI)
    shutdown_telemetry = Mock()

    with (
        patch(
            "app.core.lifecycle.initialize_telemetry",
            Mock(),
        ),
        patch(
            "app.core.lifecycle.initialize_short_term_checkpointer",
            AsyncMock(side_effect=RuntimeError("redis init failed")),
        ),
        patch(
            "app.core.lifecycle.shutdown_telemetry",
            shutdown_telemetry,
        ),
        pytest.raises(RuntimeError, match="redis init failed"),
    ):
        async with application_lifespan(application):
            pass

    shutdown_telemetry.assert_called_once_with()
