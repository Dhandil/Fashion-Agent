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
