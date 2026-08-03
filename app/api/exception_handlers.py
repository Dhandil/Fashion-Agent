from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.api.schemas.error import ErrorResponse


async def configuration_error_handler(
    _request: Request,
    exc: Exception,
) -> JSONResponse:
    """将配置异常转换成统一的 API 错误响应。"""

    # 使用统一响应模型组织错误数据
    error_response = ErrorResponse(
        code="configuration_error",
        message=str(exc),
    )

    # 将 Pydantic 模型转换成 JSON HTTP 响应
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=error_response.model_dump(),
    )


async def service_not_ready_handler(
    _request: Request,
    exc: Exception,
) -> JSONResponse:
    """将基础设施未就绪转换成不泄露连接详情的 503。"""

    error_response = ErrorResponse(
        code="service_not_ready",
        message=str(exc),
    )
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=error_response.model_dump(),
    )


async def outfit_recommendation_not_found_handler(
    _request: Request,
    exc: Exception,
) -> JSONResponse:
    """将不存在的待确认推荐转换成 404 响应。"""

    error_response = ErrorResponse(
        code="outfit_recommendation_not_found",
        message=str(exc),
    )

    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=error_response.model_dump(),
    )


async def outfit_not_found_handler(
    _request: Request,
    exc: Exception,
) -> JSONResponse:
    """将找不到已保存穿搭转换成 404 响应。"""

    error_response = ErrorResponse(
        code="outfit_not_found",
        message=str(exc),
    )

    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=error_response.model_dump(),
    )


async def outfit_feedback_not_found_handler(
    _request: Request,
    exc: Exception,
) -> JSONResponse:
    """将找不到 Outfit 反馈转换成统一的 404 响应。"""

    error_response = ErrorResponse(
        code="outfit_feedback_not_found",
        message=str(exc),
    )

    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=error_response.model_dump(),
    )


async def preference_candidate_unavailable_handler(
    _request: Request,
    exc: Exception,
) -> JSONResponse:
    """将不可确认的偏好候选转换成统一的 409 响应。"""

    error_response = ErrorResponse(
        code="preference_candidate_unavailable",
        message=str(exc),
    )

    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=error_response.model_dump(),
    )


async def preference_memory_not_found_handler(
    _request: Request,
    exc: Exception,
) -> JSONResponse:
    """将找不到长期偏好记录转换成统一的 404 响应。"""

    error_response = ErrorResponse(
        code="preference_memory_not_found",
        message=str(exc),
    )

    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=error_response.model_dump(),
    )


async def preference_memory_update_conflict_handler(
    _request: Request,
    exc: Exception,
) -> JSONResponse:
    """将长期偏好更新时间冲突转换成统一的 409 响应。"""

    error_response = ErrorResponse(
        code="preference_memory_update_conflict",
        message=str(exc),
    )

    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=error_response.model_dump(),
    )


async def style_profile_update_conflict_handler(
    _request: Request,
    exc: Exception,
) -> JSONResponse:
    """将长期档案部分更新冲突转换成统一的 409 响应。"""

    error_response = ErrorResponse(
        code="style_profile_update_conflict",
        message=str(exc),
    )

    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=error_response.model_dump(),
    )


async def wardrobe_image_error_handler(
    _request: Request,
    exc: Exception,
) -> JSONResponse:
    """将无效衣物照片转换成统一的 400 响应。"""

    error_response = ErrorResponse(
        code="wardrobe_image_invalid",
        message=str(exc),
    )

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=error_response.model_dump(),
    )


async def wardrobe_vision_provider_error_handler(
    _request: Request,
    exc: Exception,
) -> JSONResponse:
    """将照片识别未启用或暂时失败转换成统一的 503 响应。"""

    error_response = ErrorResponse(
        code="wardrobe_vision_unavailable",
        message=str(exc),
    )

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=error_response.model_dump(),
    )


async def wardrobe_item_not_found_handler(
    _request: Request,
    exc: Exception,
) -> JSONResponse:
    """将找不到衣橱单品转换成统一的 404 响应。"""

    error_response = ErrorResponse(
        code="wardrobe_item_not_found",
        message=str(exc),
    )

    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=error_response.model_dump(),
    )
