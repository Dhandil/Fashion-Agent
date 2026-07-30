"""FastAPI 数据库与仓库依赖。"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.fashion_provider import (
    FashionRepositories,
    create_postgres_fashion_repositories,
)
from app.db.session import get_database_session

# FastAPI 会为每次请求调用 get_database_session()
DatabaseSession = Annotated[
    AsyncSession,
    Depends(get_database_session),
]


async def get_fashion_repositories(
    session: DatabaseSession,
) -> FashionRepositories:
    """为当前请求创建共享同一 Session 的用户数据仓库。"""

    return create_postgres_fashion_repositories(
        session,
    )


# 路由通过这个类型声明获取请求级仓库集合
FashionRepositoriesDependency = Annotated[
    FashionRepositories,
    Depends(get_fashion_repositories),
]
