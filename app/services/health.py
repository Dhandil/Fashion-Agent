"""应用健康与基础设施就绪检查服务。"""

from typing import Literal

from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.health import (
    CapabilitiesResponse,
    CapabilityChecks,
)
from app.core.config import get_settings
from app.core.exceptions import ServiceNotReadyError
from app.rag.embeddings.huggingface import (
    create_huggingface_embeddings,
)
from app.rag.vectorstores.provider import (
    get_knowledge_vector_store,
)


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


async def assess_capabilities() -> CapabilitiesResponse:
    """评估 Agent 核心能力状态，区分"进程存活"与"能力可用"。

    所有检查只读取配置或做轻量本地操作，不发起外部模型调用，
    不向 API 暴露任何密钥或连接地址。
    """

    settings = get_settings()
    checks = CapabilityChecks()

    # ── LLM：需要密钥与模型名称 ──
    if settings.llm_api_key is not None and settings.llm_model is not None:
        checks.llm = "ok"

    # ── Embedding：配置存在且模型对象可构造（不触发权重加载）──
    try:
        create_huggingface_embeddings(settings)
        checks.embedding = "ok"
    except Exception:  # noqa: BLE001 - 能力检查必须吞掉所有异常并降级上报
        checks.embedding = "missing"

    # ── 知识库：Chroma 集合非空并读取已导入发布版本 ──
    try:
        vector_store = get_knowledge_vector_store()
        stored = vector_store.get(
            include=["metadatas"],
            limit=1,
        )
        stored_metadatas = stored.get("metadatas") or []
        if stored_metadatas and stored_metadatas[0]:
            checks.knowledge_base = "ok"
            checks.knowledge_version = stored_metadatas[0].get("release_id")
        else:
            checks.knowledge_base = "empty"
    except Exception:  # noqa: BLE001 - Chroma 未初始化或不可访问时降级为 unavailable
        # Chroma 尚未初始化或无法访问时保持默认 unavailable
        checks.knowledge_base = "unavailable"

    # ── 天气：仅检查后端是否启用（Open-Meteo 无需密钥）──
    if settings.weather_provider_backend != "disabled":
        checks.weather = "ok"

    # ── 视觉：启用时要求密钥、模型与地址齐备 ──
    if settings.wardrobe_vision_backend == "disabled":
        checks.vision = "disabled"
    elif (
        settings.wardrobe_vision_api_key is not None
        and settings.wardrobe_vision_model is not None
        and settings.wardrobe_vision_base_url is not None
    ):
        checks.vision = "ok"
    else:
        checks.vision = "missing"

    # 整体状态：全部已检查项就绪才算 ok；禁用项不参与判定
    required = (
        checks.llm,
        checks.embedding,
        checks.knowledge_base,
    )
    status = "ok" if all(item == "ok" for item in required) else "degraded"
    return CapabilitiesResponse(status=status, checks=checks)
