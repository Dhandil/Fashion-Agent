"""基础设施就绪检查服务测试。"""

from contextlib import ExitStack
from unittest.mock import AsyncMock, Mock, patch

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import ServiceNotReadyError
from app.services.health import (
    assess_capabilities,
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


# ── 能力评估 assess_capabilities ──


def _build_vector_store(
    *,
    knowledge_metadatas: list[dict[str, object]] | None = None,
    knowledge_error: Exception | None = None,
) -> Mock:
    """构造能力评估用到的 vector_store mock。"""

    vector_store = Mock()
    if knowledge_error is not None:
        vector_store.get.side_effect = knowledge_error
    else:
        vector_store.get.return_value = {
            "metadatas": knowledge_metadatas or [],
        }
    return vector_store


def _capability_patches(settings: Settings, vector_store: Mock) -> ExitStack:
    """返回能力评估依赖的 patch 上下文管理器。"""

    stack = ExitStack()
    stack.enter_context(
        patch(
            "app.services.health.get_settings",
            return_value=settings,
        ),
    )
    stack.enter_context(
        patch(
            "app.services.health.get_knowledge_vector_store",
            return_value=vector_store,
        ),
    )
    return stack


@pytest.mark.anyio
async def test_capabilities_reports_unconfigured_state() -> None:
    """验证未配置外部服务时能力检查如实上报 missing/disabled。"""

    settings = Settings(
        _env_file=None,
    )
    vector_store = _build_vector_store()

    with _capability_patches(settings, vector_store):
        response = await assess_capabilities()

    assert response.status == "degraded"
    assert response.checks.llm == "missing"
    assert response.checks.embedding == "ok"
    assert response.checks.knowledge_base == "empty"
    assert response.checks.knowledge_version is None
    assert response.checks.weather == "disabled"
    assert response.checks.vision == "disabled"


@pytest.mark.anyio
async def test_capabilities_reports_configured_services() -> None:
    """验证 LLM/天气/视觉配置齐备且知识库非空时整体为 ok。"""

    settings = Settings(
        _env_file=None,
        llm_api_key="test-secret-key",
        llm_model="deepseek-chat",
        weather_provider_backend="open_meteo",
        wardrobe_vision_backend="openai_compatible",
        wardrobe_vision_api_key="vision-key",
        wardrobe_vision_model="glm-4v-flash",
        wardrobe_vision_base_url="https://example.com/v1",
    )
    vector_store = _build_vector_store(
        knowledge_metadatas=[
            {"release_id": "fashion-knowledge-2.8.0"},
        ],
    )

    with _capability_patches(settings, vector_store):
        response = await assess_capabilities()

    assert response.status == "ok"
    assert response.checks.llm == "ok"
    assert response.checks.embedding == "ok"
    assert response.checks.knowledge_base == "ok"
    assert response.checks.knowledge_version == "fashion-knowledge-2.8.0"
    assert response.checks.weather == "ok"
    assert response.checks.vision == "ok"


@pytest.mark.anyio
async def test_capabilities_hides_chroma_failure() -> None:
    """验证 Chroma 不可访问时知识库标记为 unavailable 而非抛异常。"""

    settings = Settings(
        _env_file=None,
        llm_api_key="test-secret-key",
        llm_model="deepseek-chat",
    )
    vector_store = _build_vector_store(
        knowledge_error=RuntimeError("chroma broken"),
    )

    with _capability_patches(settings, vector_store):
        response = await assess_capabilities()

    assert response.status == "degraded"
    assert response.checks.llm == "ok"
    assert response.checks.knowledge_base == "unavailable"
    assert response.checks.knowledge_version is None


@pytest.mark.anyio
async def test_capabilities_vision_requires_full_config() -> None:
    """验证视觉后端启用但配置不完整时标记为 missing。"""

    settings = Settings(
        _env_file=None,
        wardrobe_vision_backend="openai_compatible",
        # 缺少 api_key
        wardrobe_vision_model="glm-4v-flash",
        wardrobe_vision_base_url="https://example.com/v1",
    )
    vector_store = _build_vector_store()

    with _capability_patches(settings, vector_store):
        response = await assess_capabilities()

    assert response.checks.vision == "missing"
