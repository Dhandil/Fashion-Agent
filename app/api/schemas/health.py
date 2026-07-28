from pydantic import BaseModel


class HealthResponse(BaseModel):
    """健康检查接口的响应模型。"""

    # 服务运行状态，例如"ok"
    status: str

    # 当前应用名称
    app_name: str

    # 当前运行环境，例如 development
    environment: str