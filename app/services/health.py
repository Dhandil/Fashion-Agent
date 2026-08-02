"""应用健康与基础设施就绪检查服务。"""

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ServiceNotReadyError


async def ensure_database_ready(
    session: AsyncSession,
) -> None:
    """执行最小只读查询，确认 PostgreSQL 可以处理请求。"""

    try:
        result = await session.execute(text("SELECT 1"))
        if result.scalar_one() != 1:
            raise ServiceNotReadyError(
                "数据库就绪检查返回异常结果",
            )
    except ServiceNotReadyError:
        raise
    except SQLAlchemyError as exc:
        # 不向 API 暴露连接地址、账号或驱动异常详情。
        raise ServiceNotReadyError(
            "数据库暂时不可用",
        ) from exc
