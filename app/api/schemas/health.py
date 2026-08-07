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


class CapabilityChecks(BaseModel):
    """Agent 核心能力的状态汇总。

    取值约定：
    - llm / embedding：ok | missing
    - knowledge_base：ok | empty | unavailable
    - weather / vision：ok | disabled | missing
    """

    llm: str = "missing"
    embedding: str = "missing"
    knowledge_base: str = "unavailable"
    knowledge_version: str | None = None
    weather: str = "disabled"
    vision: str = "disabled"


class CapabilitiesResponse(BaseModel):
    """Agent 能力检查响应；能力缺失不影响进程存活。"""

    status: str = "degraded"
    checks: CapabilityChecks
