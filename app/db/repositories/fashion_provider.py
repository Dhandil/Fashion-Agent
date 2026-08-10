"""用户时尚数据 PostgreSQL 仓库装配。"""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

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
from app.db.repositories.postgres_wardrobe_image_asset import (
    PostgresWardrobeImageAssetRepository,
)
from app.domain.repositories.outfit import (
    OutfitRepository,
)
from app.domain.repositories.outfit_feedback import (
    OutfitFeedbackRepository,
)
from app.domain.repositories.preference_memory import (
    PreferenceMemoryRepository,
)
from app.domain.repositories.style_profile import (
    StyleProfileRepository,
)
from app.domain.repositories.wardrobe import (
    WardrobeRepository,
)
from app.domain.repositories.wardrobe_image_asset import (
    WardrobeImageAssetRepository,
)


@dataclass(
    frozen=True,
    slots=True,
)
class FashionRepositories:
    """一次业务操作需要使用的用户时尚数据仓库。"""

    style_profiles: StyleProfileRepository
    preference_memories: PreferenceMemoryRepository
    wardrobe: WardrobeRepository
    outfits: OutfitRepository
    outfit_feedback: OutfitFeedbackRepository
    # 旧测试和内存装配可以暂不提供图片资产仓库；PostgreSQL 装配会注入实现
    wardrobe_image_assets: WardrobeImageAssetRepository | None = None


def create_postgres_fashion_repositories(
    session: AsyncSession,
) -> FashionRepositories:
    """使用同一个 Session 创建 PostgreSQL 仓库集合。"""

    return FashionRepositories(
        style_profiles=PostgresStyleProfileRepository(
            session,
        ),
        preference_memories=(
            PostgresPreferenceMemoryRepository(
                session,
            )
        ),
        wardrobe=PostgresWardrobeRepository(
            session,
        ),
        wardrobe_image_assets=PostgresWardrobeImageAssetRepository(
            session,
        ),
        outfits=PostgresOutfitRepository(
            session,
        ),
        outfit_feedback=(
            PostgresOutfitFeedbackRepository(
                session,
            )
        ),
    )
