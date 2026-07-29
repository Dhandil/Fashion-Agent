from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """API 统一响应错误模型。"""

    # 稳定的错误代码，方便前端判断错误类型
    code: str

    # 给用户或开发者阅读的错误说明
    message: str