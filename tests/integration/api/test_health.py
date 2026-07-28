from fastapi.testclient import TestClient

from app.core.config import get_settings
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