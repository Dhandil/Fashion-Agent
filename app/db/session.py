"""PostgreSQL 异步连接与会话管理。"""

from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings
from app.core.exceptions import ConfigurationError


@lru_cache
def get_database_engine() -> AsyncEngine:
    """根据项目配置创建并缓存异步数据库 Engine。"""

    # 读取项目统一配置
    settings = get_settings()

    # PostgreSQL 模式必须提供数据库连接地址
    if settings.database_url is None:
        raise ConfigurationError(
            "未配置 DATABASE_URL，无法创建数据库连接",
        )

    # SecretStr 需要显式读取真实连接字符串
    database_url = settings.database_url.get_secret_value()

    # Engine 负责管理数据库连接池
    return create_async_engine(
        database_url,
        echo=settings.database_echo,
        pool_pre_ping=True,
    )


@lru_cache
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """创建并缓存异步数据库 Session 工厂。"""

    # Session 工厂复用同一个数据库 Engine
    engine = get_database_engine()

    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def get_database_session() -> AsyncIterator[AsyncSession]:
    """为一次业务操作提供独立的异步数据库 Session。"""

    # 每次调用工厂都会创建一个新的 Session
    session_factory = get_session_factory()

    # async with 会在使用完成后自动关闭 Session
    async with session_factory() as session:
        yield session