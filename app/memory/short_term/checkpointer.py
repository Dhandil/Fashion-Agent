"""LangGraph 短期记忆 Checkpointer 的创建和生命周期管理。"""

from functools import lru_cache

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.redis.aio import AsyncRedisSaver

from app.core.config import Settings, get_settings
from app.core.exceptions import ConfigurationError


def create_short_term_checkpointer(
    settings: Settings,
) -> BaseCheckpointSaver[str]:
    """根据配置创建内存或 Redis Checkpointer。"""

    if settings.short_term_memory_backend == "memory":
        # 内存实现适合单进程开发和隔离测试，进程退出后状态会丢失
        return InMemorySaver()

    if settings.redis_url is None:
        raise ConfigurationError(
            "使用 Redis 短期记忆时必须配置 REDIS_URL",
        )

    # TTL 单位由 Redis Checkpointer 定义为分钟
    ttl = {
        "default_ttl": settings.redis_checkpoint_ttl_minutes,
        "refresh_on_read": True,
    }
    return AsyncRedisSaver(
        redis_url=settings.redis_url.get_secret_value(),
        ttl=ttl,
    )


@lru_cache
def get_short_term_checkpointer() -> BaseCheckpointSaver[str]:
    """创建并缓存跨请求共享的短期记忆 Checkpointer。"""

    return create_short_term_checkpointer(get_settings())


async def initialize_short_term_checkpointer() -> None:
    """在应用启动时初始化 Redis 索引；内存后端无需额外操作。"""

    settings = get_settings()
    checkpointer = get_short_term_checkpointer()
    if settings.short_term_memory_backend != "redis":
        return

    redis_checkpointer = checkpointer
    if not isinstance(redis_checkpointer, AsyncRedisSaver):
        raise ConfigurationError(
            "Redis 短期记忆后端没有创建 Redis Checkpointer",
        )

    try:
        await redis_checkpointer.asetup()
    except Exception:
        # 初始化失败时也关闭已经创建的客户端，避免连接池泄漏
        await redis_checkpointer.__aexit__(None, None, None)
        get_short_term_checkpointer.cache_clear()
        raise


async def close_short_term_checkpointer() -> None:
    """关闭 Redis 连接并清除缓存，内存后端只需释放对象。"""

    if get_short_term_checkpointer.cache_info().currsize == 0:
        return

    checkpointer = get_short_term_checkpointer()
    try:
        if isinstance(checkpointer, AsyncRedisSaver):
            await checkpointer.__aexit__(None, None, None)
    finally:
        get_short_term_checkpointer.cache_clear()
