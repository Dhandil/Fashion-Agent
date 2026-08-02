"""应用健康与基础设施就绪检查服务。"""

from typing import Literal

from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import ServiceNotReadyError


async def ensure_database_ready(
    session: AsyncSession,
) -> None:
    """执行最小只读查询，确认 PostgreSQL 可以处理请求。"""

    try:
        result = await session.execute(text("SELECT 1"))
        if result.scalar_one() != 1:
            raise ServiceNotReadyError(
                "数据库就绪检查返回异常结果",
            )
    except ServiceNotReadyError:
        raise
    except SQLAlchemyError as exc:
        # 不向 API 暴露连接地址、账号或驱动异常详情。
        raise ServiceNotReadyError(
            "数据库暂时不可用",
        ) from exc


async def ensure_short_term_memory_ready() -> Literal[
    "memory",
    "ok",
]:
    """确认当前短期记忆后端可以接受请求。"""

    settings = get_settings()
    if settings.short_term_memory_backend == "memory":
        return "memory"

    if settings.redis_url is None:
        raise ServiceNotReadyError(
            "短期记忆暂时不可用",
        )

    client = Redis.from_url(
        settings.redis_url.get_secret_value(),
        decode_responses=False,
    )
    try:
        ping_result = client.ping()
        redis_is_ready = (
            ping_result
            if isinstance(ping_result, bool)
            else await ping_result
        )
        if not redis_is_ready:
            raise ServiceNotReadyError(
                "短期记忆暂时不可用",
            )
    except ServiceNotReadyError:
        raise
    except (RedisError, OSError) as exc:
        # 不向 API 暴露 Redis 地址、密码或底层连接异常。
        raise ServiceNotReadyError(
            "短期记忆暂时不可用",
        ) from exc
    finally:
        await client.aclose()

    return "ok"
