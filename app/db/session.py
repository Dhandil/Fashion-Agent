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
    """为一次请求提供带事务管理的异步数据库 Session。"""

    # 每次调用工厂都会创建一个新的请求级 Session
    session_factory = get_session_factory()

    # async with 保证请求结束后关闭 Session
    async with session_factory() as session:
        try:
            # 把 Session 交给 FastAPI 路由及其依赖使用
            yield session

            # 路由及依赖正常结束后统一提交事务
            await session.commit()

        except Exception:
            # 任意业务异常发生时撤销本次请求的全部数据库修改
            await session.rollback()

            # 保留原始异常，让 FastAPI 的异常处理器继续处理
            raise


async def close_database_connections() -> None:
    """应用停止时释放已创建的数据库连接池和缓存工厂。"""

    # 不为了关闭而新建 Engine；只有实际使用过数据库才执行 dispose。
    if get_database_engine.cache_info().currsize > 0:
        engine = get_database_engine()
        await engine.dispose()

    get_session_factory.cache_clear()
    get_database_engine.cache_clear()
