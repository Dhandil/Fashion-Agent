from fastapi import FastAPI

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.api.router import api_router


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

    return application



# 创建供 Uvicorn 启动的全局应用实例
app = create_app()