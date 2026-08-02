from fastapi import APIRouter

from app.api.dependencies.database import DatabaseSession
from app.api.schemas.health import (
    HealthResponse,
    ReadinessChecks,
    ReadinessResponse,
)
from app.core.config import get_settings
from app.services.health import (
    ensure_database_ready,
    ensure_short_term_memory_ready,
)

# 创建健康检查路由对象
router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="健康检查",
)
def health_check() -> HealthResponse:
    """返回应用当前的运行状态。"""

    # 获取应用配置
    settings = get_settings()

    # 创建并返回符合 HealthResponse 结构的响应
    return HealthResponse(
        status="ok",
        app_name=settings.app_name,
        environment=settings.app_env,
    )


@router.get(
    "/health/ready",
    response_model=ReadinessResponse,
    summary="数据库就绪检查",
)
async def readiness_check(
    session: DatabaseSession,
) -> ReadinessResponse:
    """确认 PostgreSQL 和短期记忆均可处理业务请求。"""

    await ensure_database_ready(session)
    memory_status = await ensure_short_term_memory_ready()
    return ReadinessResponse(
        status="ready",
        checks=ReadinessChecks(
            database="ok",
            short_term_memory=memory_status,
        ),
    )
