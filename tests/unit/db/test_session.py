"""数据库连接与会话管理测试。"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, Mock, patch

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
)

from app.core.config import Settings
from app.core.exceptions import ConfigurationError
from app.db.session import (
    close_database_connections,
    get_database_engine,
    get_database_session,
)


def test_get_database_engine_requires_database_url() -> None:
    """验证缺少数据库地址时抛出统一配置异常。"""

    # 创建一份明确不包含数据库地址的测试配置
    settings = Settings(
        _env_file=None,
        database_url=None,
    )

    # 清除其他测试可能创建的 Engine 缓存
    get_database_engine.cache_clear()

    # 替换真实配置，并验证缺少数据库地址时报告明确错误
    with (
        patch(
            "app.db.session.get_settings",
            return_value=settings,
        ),
        pytest.raises(
            ConfigurationError,
            match="DATABASE_URL",
        ),
    ):
        get_database_engine()

    # 测试结束后再次清理缓存，避免影响其他测试
    get_database_engine.cache_clear()


def test_get_database_engine_uses_project_settings() -> None:
    """验证 Engine 使用数据库配置正确创建。"""

    # 创建包含测试数据库地址的配置
    settings = Settings(
        _env_file=None,
        database_url=("postgresql+asyncpg://fashion_agent:secret@localhost:5432/fashion_agent"),
        database_echo=True,
    )

    # 模拟 SQLAlchemy 创建出的异步 Engine
    fake_engine = Mock(spec=AsyncEngine)

    # 确保本次调用不会读取之前缓存的 Engine
    get_database_engine.cache_clear()

    with (
        patch(
            "app.db.session.get_settings",
            return_value=settings,
        ),
        patch(
            "app.db.session.create_async_engine",
            return_value=fake_engine,
        ) as mocked_create_engine,
    ):
        engine = get_database_engine()

    # 应该返回 SQLAlchemy 工厂创建的 Engine
    assert engine is fake_engine

    # 验证连接地址和 Engine 参数传递正确
    mocked_create_engine.assert_called_once_with(
        ("postgresql+asyncpg://fashion_agent:secret@localhost:5432/fashion_agent"),
        echo=True,
        pool_pre_ping=True,
    )

    # 防止假的 Engine 留在函数缓存中
    get_database_engine.cache_clear()


@pytest.mark.anyio
async def test_database_session_commits_successful_request() -> None:
    """验证请求正常完成后提交数据库事务。"""

    fake_session = AsyncMock(spec=AsyncSession)

    # 模拟 session_factory() 返回的异步上下文管理器
    @asynccontextmanager
    async def session_context() -> AsyncIterator[AsyncSession]:
        yield fake_session

    fake_session_factory = Mock(
        return_value=session_context(),
    )

    with patch(
        "app.db.session.get_session_factory",
        return_value=fake_session_factory,
    ):
        session_generator = get_database_session()

        # 第一次执行到 yield，取得路由使用的 Session
        yielded_session = await anext(
            session_generator,
        )

        assert yielded_session is fake_session

        # 第二次继续生成器，模拟路由正常结束
        with pytest.raises(StopAsyncIteration):
            await anext(session_generator)

    fake_session.commit.assert_awaited_once()
    fake_session.rollback.assert_not_awaited()


@pytest.mark.anyio
async def test_database_session_rolls_back_failed_request() -> None:
    """验证请求抛出异常时回滚数据库事务。"""

    fake_session = AsyncMock(spec=AsyncSession)

    @asynccontextmanager
    async def session_context() -> AsyncIterator[AsyncSession]:
        yield fake_session

    fake_session_factory = Mock(
        return_value=session_context(),
    )

    with patch(
        "app.db.session.get_session_factory",
        return_value=fake_session_factory,
    ):
        session_generator = get_database_session()

        await anext(session_generator)

        # 把路由异常送回生成器，模拟请求执行失败
        with pytest.raises(
            RuntimeError,
            match="测试业务异常",
        ):
            await session_generator.athrow(
                RuntimeError("测试业务异常"),
            )

    fake_session.rollback.assert_awaited_once()
    fake_session.commit.assert_not_awaited()


@pytest.mark.anyio
async def test_close_database_connections_disposes_cached_engine() -> None:
    """验证应用关闭时释放已创建的连接池并清理缓存。"""

    fake_engine = AsyncMock(spec=AsyncEngine)
    cache_info = Mock(currsize=1)

    with (
        patch(
            "app.db.session.get_database_engine",
            return_value=fake_engine,
        ) as mocked_get_engine,
        patch(
            "app.db.session.get_session_factory",
        ) as mocked_get_factory,
    ):
        mocked_get_engine.cache_info.return_value = cache_info
        await close_database_connections()

    fake_engine.dispose.assert_awaited_once()
    mocked_get_factory.cache_clear.assert_called_once()
    mocked_get_engine.cache_clear.assert_called_once()
