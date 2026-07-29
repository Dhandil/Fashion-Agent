"""数据库连接与会话管理测试。"""

from unittest.mock import Mock, patch
from sqlalchemy.ext.asyncio import AsyncEngine
import pytest

from app.core.config import Settings
from app.core.exceptions import ConfigurationError
from app.db.session import get_database_engine


def test_get_database_engine_requires_database_url() -> None:
    """验证缺少数据库地址时抛出统一配置异常。"""

    # 创建一份明确不包含数据库地址的测试配置
    settings = Settings(
        _env_file=None,
        database_url=None,
    )

    # 清除其他测试可能创建的 Engine 缓存
    get_database_engine.cache_clear()

    # 将数据库模块获取到的真实配置替换为测试配置
    with patch(
        "app.db.session.get_settings",
        return_value=settings,
    ):
        # 没有 DATABASE_URL 时必须明确报告配置错误
        with pytest.raises(
            ConfigurationError,
            match="DATABASE_URL",
        ):
            get_database_engine()

    # 测试结束后再次清理缓存，避免影响其他测试
    get_database_engine.cache_clear()


def test_get_database_engine_uses_project_settings() -> None:
    """验证 Engine 使用数据库配置正确创建。"""

    # 创建包含测试数据库地址的配置
    settings = Settings(
        _env_file=None,
        database_url=(
            "postgresql+asyncpg://"
            "fashion_agent:secret@localhost:5432/fashion_agent"
        ),
        database_echo=True,
    )

    # 模拟 SQLAlchemy 创建出的异步 Engine
    fake_engine = Mock(spec=AsyncEngine)

    # 确保本次调用不会读取之前缓存的 Engine
    get_database_engine.cache_clear()

    with (
        patch(
            "app.db.session.get_settings",
            return_value=settings,
        ),
        patch(
            "app.db.session.create_async_engine",
            return_value=fake_engine,
        ) as mocked_create_engine,
    ):
        engine = get_database_engine()

    # 应该返回 SQLAlchemy 工厂创建的 Engine
    assert engine is fake_engine

    # 验证连接地址和 Engine 参数传递正确
    mocked_create_engine.assert_called_once_with(
        (
            "postgresql+asyncpg://"
            "fashion_agent:secret@localhost:5432/fashion_agent"
        ),
        echo=True,
        pool_pre_ping=True,
    )

    # 防止假的 Engine 留在函数缓存中
    get_database_engine.cache_clear()