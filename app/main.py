from fastapi import FastAPI

from app.api.exception_handlers import (
    configuration_error_handler,
    outfit_feedback_not_found_handler,
    outfit_not_found_handler,
    outfit_recommendation_not_found_handler,
    preference_candidate_unavailable_handler,
    preference_memory_not_found_handler,
    preference_memory_update_conflict_handler,
    service_not_ready_handler,
    style_profile_update_conflict_handler,
    wardrobe_item_not_found_handler,
)
from app.api.middleware.request_id import (
    register_request_id_middleware,
)
from app.api.router import api_router
from app.core.config import get_settings
from app.core.exceptions import (
    ConfigurationError,
    OutfitFeedbackNotFoundError,
    OutfitNotFoundError,
    OutfitRecommendationNotFoundError,
    PreferenceCandidateUnavailableError,
    PreferenceMemoryNotFoundError,
    PreferenceMemoryUpdateConflictError,
    ServiceNotReadyError,
    StyleProfileUpdateConflictError,
    WardrobeItemNotFoundError,
)
from app.core.lifecycle import application_lifespan
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
        lifespan=application_lifespan,
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
        ServiceNotReadyError,
        service_not_ready_handler,
    )

    # 为所有 HTTP 请求生成或传播可跨日志关联的 request_id
    register_request_id_middleware(application)
    application.add_exception_handler(
        OutfitRecommendationNotFoundError,
        outfit_recommendation_not_found_handler,
    )
    application.add_exception_handler(
        OutfitNotFoundError,
        outfit_not_found_handler,
    )
    application.add_exception_handler(
        OutfitFeedbackNotFoundError,
        outfit_feedback_not_found_handler,
    )
    application.add_exception_handler(
        PreferenceCandidateUnavailableError,
        preference_candidate_unavailable_handler,
    )
    application.add_exception_handler(
        PreferenceMemoryNotFoundError,
        preference_memory_not_found_handler,
    )
    application.add_exception_handler(
        PreferenceMemoryUpdateConflictError,
        preference_memory_update_conflict_handler,
    )
    application.add_exception_handler(
        StyleProfileUpdateConflictError,
        style_profile_update_conflict_handler,
    )
    application.add_exception_handler(
        WardrobeItemNotFoundError,
        wardrobe_item_not_found_handler,
    )

    return application


# 创建供 Uvicorn 启动的全局应用实例
app = create_app()
