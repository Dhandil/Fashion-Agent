from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, Mock

from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_database_session
from app.main import create_app

# 创建独立的 FastAPI 测试应用
application = create_app()

# 创建测试客户端，不需要启动 Uvicorn
client = TestClient(application)


def test_health_check_returns_application_status() -> None:
    """验证健康检查接口返回正确的应用状态。"""

    # 向 FastAPI 测试应用发送 GET 请求
    response = client.get("/api/v1/health")

    # 验证 HTTP 状态码为 200，表示请求成功
    assert response.status_code == 200

    # 获取当前配置，拥有验证接口返回内容
    settings = get_settings()

    # response.json() 会把 JSON 响应转换成 Python 字典
    assert response.json() == {
        "status": "ok",
        "app_name": settings.app_name,
        "environment": settings.app_env,
    }


def test_readiness_check_returns_database_status() -> None:
    """验证数据库可查询时 readiness 返回 ready。"""

    session = AsyncMock(spec=AsyncSession)
    result = Mock()
    result.scalar_one.return_value = 1
    session.execute.return_value = result

    async def override_session() -> AsyncIterator[AsyncSession]:
        """提供固定的就绪数据库 Session。"""

        yield session

    application.dependency_overrides[get_database_session] = (
        override_session
    )
    try:
        response = client.get("/api/v1/health/ready")
    finally:
        application.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "checks": {"database": "ok"},
    }


def test_readiness_check_returns_safe_503() -> None:
    """验证数据库失败时返回稳定 503 且不泄露连接信息。"""

    session = AsyncMock(spec=AsyncSession)
    session.execute.side_effect = SQLAlchemyError(
        "postgresql://user:secret@database",
    )

    async def override_session() -> AsyncIterator[AsyncSession]:
        """提供会抛出驱动异常的数据库 Session。"""

        yield session

    application.dependency_overrides[get_database_session] = (
        override_session
    )
    try:
        response = client.get("/api/v1/health/ready")
    finally:
        application.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {
        "code": "service_not_ready",
        "message": "数据库暂时不可用",
    }
    assert "secret" not in response.text
