"""FastAPI 数据库依赖测试。"""

from unittest.mock import (
    AsyncMock,
    Mock,
    patch,
)

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.database import (
    get_fashion_repositories,
)
from app.db.repositories.fashion_provider import (
    FashionRepositories,
)


@pytest.mark.anyio
async def test_database_dependency_uses_request_session() -> None:
    """验证仓库依赖使用当前请求传入的 Session。"""

    # 模拟 FastAPI 为当前请求创建的数据库 Session
    session = AsyncMock(spec=AsyncSession)

    # 模拟仓库工厂返回的仓库集合
    fake_repositories = Mock(
        spec=FashionRepositories,
    )

    with patch(
        ("app.api.dependencies.database.create_postgres_fashion_repositories"),
        return_value=fake_repositories,
    ) as mocked_create_repositories:
        repositories = await get_fashion_repositories(
            session,
        )

    # 仓库工厂必须收到当前请求的同一个 Session
    mocked_create_repositories.assert_called_once_with(
        session,
    )

    # 依赖函数应该原样返回工厂创建的仓库集合
    assert repositories is fake_repositories
