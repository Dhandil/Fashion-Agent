"""基础设施就绪检查服务测试。"""

from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ServiceNotReadyError
from app.services.health import ensure_database_ready


@pytest.mark.anyio
async def test_database_readiness_accepts_select_one() -> None:
    """验证 PostgreSQL 返回预期标量时判定为就绪。"""

    session = AsyncMock(spec=AsyncSession)
    result = Mock()
    result.scalar_one.return_value = 1
    session.execute.return_value = result

    await ensure_database_ready(session)

    statement = session.execute.await_args.args[0]
    assert str(statement) == "SELECT 1"


@pytest.mark.anyio
async def test_database_readiness_hides_driver_error() -> None:
    """验证数据库异常转换成稳定错误且不暴露连接详情。"""

    session = AsyncMock(spec=AsyncSession)
    session.execute.side_effect = SQLAlchemyError(
        "postgresql://user:secret@database",
    )

    with pytest.raises(
        ServiceNotReadyError,
        match="数据库暂时不可用",
    ) as captured:
        await ensure_database_ready(session)

    assert "secret" not in str(captured.value)
