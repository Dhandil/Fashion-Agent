"""PostgreSQL 集成测试资源管理。"""

from collections.abc import AsyncIterator

import pytest

from app.db.session import (
    get_database_engine,
    get_session_factory,
)


@pytest.fixture(autouse=True)
async def reset_database_resources() -> AsyncIterator[None]:
    """每条数据库测试结束后释放连接池并清除缓存。"""

    # yield 之前是测试准备阶段
    # 当前没有额外准备，因此直接交给测试函数执行
    yield

    # fixture 的清理阶段仍运行在当前测试的事件循环中
    engine = get_database_engine()

    # 关闭连接池中的 asyncpg 连接
    await engine.dispose()

    # 清除绑定旧 Engine 的 Session 工厂缓存
    get_session_factory.cache_clear()

    # 清除已经释放的 Engine 缓存
    get_database_engine.cache_clear()