"""用户时尚数据仓库装配测试。"""

from unittest.mock import AsyncMock

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.fashion_provider import (
    create_postgres_fashion_repositories,
)
from app.db.repositories.postgres_outfit import (
    PostgresOutfitRepository,
)
from app.db.repositories.postgres_outfit_feedback import (
    PostgresOutfitFeedbackRepository,
)
from app.db.repositories.postgres_preference_memory import (
    PostgresPreferenceMemoryRepository,
)
from app.db.repositories.postgres_style_profile import (
    PostgresStyleProfileRepository,
)
from app.db.repositories.postgres_wardrobe import (
    PostgresWardrobeRepository,
)


def test_fashion_repositories_share_database_session() -> None:
    """验证三个 PostgreSQL 仓库共享同一个数据库 Session。"""

    # 模拟一次 API 请求创建的异步 Session
    session = AsyncMock(spec=AsyncSession)

    repositories = create_postgres_fashion_repositories(
        session,
    )

    # 验证工厂创建了正确的 PostgreSQL 仓库实现
    assert isinstance(
        repositories.style_profiles,
        PostgresStyleProfileRepository,
    )
    assert isinstance(
        repositories.preference_memories,
        PostgresPreferenceMemoryRepository,
    )
    assert isinstance(
        repositories.wardrobe,
        PostgresWardrobeRepository,
    )
    assert isinstance(
        repositories.outfits,
        PostgresOutfitRepository,
    )
    assert isinstance(
        repositories.outfit_feedback,
        PostgresOutfitFeedbackRepository,
    )

    # 所有仓库必须共享同一个请求级 Session
    assert repositories.style_profiles._session is session
    assert repositories.preference_memories._session is session
    assert repositories.wardrobe._session is session
    assert repositories.outfits._session is session
    assert repositories.outfit_feedback._session is session
