"""基础设施就绪检查服务测试。"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import ServiceNotReadyError
from app.services.health import (
    ensure_database_ready,
    ensure_short_term_memory_ready,
)


@pytest.mark.anyio
async def test_database_readiness_accepts_select_one() -> None:
    """验证 PostgreSQL 返回预期标量时判定为就绪。"""

    session = AsyncMock(spec=AsyncSession)
    result = Mock()
    result.scalar_one.return_value = 1
    session.execute.return_value = result

    await ensure_database_ready(session)

    statement = session.execute.await_args.args[0]
    assert str(statement) == "SELECT 1"


@pytest.mark.anyio
async def test_database_readiness_hides_driver_error() -> None:
    """验证数据库异常转换成稳定错误且不暴露连接详情。"""

    session = AsyncMock(spec=AsyncSession)
    session.execute.side_effect = SQLAlchemyError(
        "postgresql://user:secret@database",
    )

    with pytest.raises(
        ServiceNotReadyError,
        match="数据库暂时不可用",
    ) as captured:
        await ensure_database_ready(session)

    assert "secret" not in str(captured.value)


@pytest.mark.anyio
async def test_memory_readiness_does_not_connect_to_redis() -> None:
    """验证内存后端无需创建 Redis 客户端。"""

    settings = Settings(_env_file=None)

    with (
        patch(
            "app.services.health.get_settings",
            return_value=settings,
        ),
        patch("app.services.health.Redis.from_url") as from_url,
    ):
        status = await ensure_short_term_memory_ready()

    assert status == "memory"
    from_url.assert_not_called()


@pytest.mark.anyio
async def test_redis_readiness_pings_and_closes_client() -> None:
    """验证 Redis 后端执行 ping 并释放临时健康检查连接。"""

    settings = Settings(
        _env_file=None,
        short_term_memory_backend="redis",
        redis_url="redis://localhost:6379/0",
    )
    client = Mock()
    client.ping = AsyncMock(return_value=True)
    client.aclose = AsyncMock()

    with (
        patch(
            "app.services.health.get_settings",
            return_value=settings,
        ),
        patch(
            "app.services.health.Redis.from_url",
            return_value=client,
        ),
    ):
        status = await ensure_short_term_memory_ready()

    assert status == "ok"
    client.ping.assert_awaited_once()
    client.aclose.assert_awaited_once()


@pytest.mark.anyio
async def test_redis_readiness_hides_connection_details() -> None:
    """验证 Redis 异常转换为不泄露连接信息的领域错误。"""

    settings = Settings(
        _env_file=None,
        short_term_memory_backend="redis",
        redis_url="redis://:secret@localhost:6379/0",
    )
    client = Mock()
    client.ping = AsyncMock(
        side_effect=RedisConnectionError(
            "redis://:secret@localhost:6379/0",
        ),
    )
    client.aclose = AsyncMock()

    with (
        patch(
            "app.services.health.get_settings",
            return_value=settings,
        ),
        patch(
            "app.services.health.Redis.from_url",
            return_value=client,
        ),
        pytest.raises(
            ServiceNotReadyError,
            match="短期记忆暂时不可用",
        ) as error,
    ):
        await ensure_short_term_memory_ready()

    assert "secret" not in str(error.value)
    client.aclose.assert_awaited_once()
