from fastapi import APIRouter

from app.api.schemas.health import HealthResponse
from app.core.config import get_settings


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