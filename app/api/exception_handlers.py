from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.api.schemas.error import ErrorResponse
from app.core.exceptions import ConfigurationError


async def configuration_error_handler(
    _request: Request,
    exc: ConfigurationError,
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