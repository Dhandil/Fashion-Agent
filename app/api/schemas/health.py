from pydantic import BaseModel


class HealthResponse(BaseModel):
    """健康检查接口的响应模型。"""

    # 服务运行状态，例如"ok"
    status: str

    # 当前应用名称
    app_name: str

    # 当前运行环境，例如 development
    environment: str


class ReadinessChecks(BaseModel):
    """当前 readiness 端点覆盖的基础设施状态。"""

    database: str
    short_term_memory: str


class ReadinessResponse(BaseModel):
    """应用能够处理持久化业务请求时的响应。"""

    status: str
    checks: ReadinessChecks
