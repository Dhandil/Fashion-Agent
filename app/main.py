from fastapi import FastAPI

from app.api.exception_handlers import (
    configuration_error_handler,
    outfit_recommendation_not_found_handler,
)
from app.api.router import api_router
from app.core.config import get_settings
from app.core.exceptions import (
    ConfigurationError,
    OutfitRecommendationNotFoundError,
)
from app.core.logging import setup_logging


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用实例。"""

    # 读取全局配置
    settings = get_settings()

    # 使用配置中的日志级别初始化日志系统
    setup_logging(settings.log_level)

    # 创建 FastAPI 应用对象
    application = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
    )

    # 注册健康检查路由，并统一添加 API 版本前缀
    application.include_router(
        api_router,
        prefix="/api/v1",
    )

    # 注册配置异常处理器
    application.add_exception_handler(
        ConfigurationError,
        configuration_error_handler,
    )
    application.add_exception_handler(
        OutfitRecommendationNotFoundError,
        outfit_recommendation_not_found_handler,
    )

    return application



# 创建供 Uvicorn 启动的全局应用实例
app = create_app()
