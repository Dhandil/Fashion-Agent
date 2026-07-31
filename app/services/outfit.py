"""用户确认后保存穿搭推荐的应用服务。"""

from dataclasses import dataclass
from uuid import UUID, uuid5

from app.agents.graphs.shopping import ShoppingGraph
from app.core.exceptions import (
    OutfitNotFoundError,
    OutfitRecommendationNotFoundError,
)
from app.domain.entities.outfit import (
    Outfit,
    OutfitRecommendation,
)
from app.domain.repositories.outfit import OutfitRepository

# 固定命名空间保证同一用户、同一会话重复确认时得到相同 Outfit ID
OUTFIT_ID_NAMESPACE = UUID(
    "3e18d4b2-d864-4c33-8aeb-33bb376e8817",
)


@dataclass(
    frozen=True,
    slots=True,
)
class SavedOutfitPage:
    """一次已保存 Outfit 分页查询结果。"""

    items: tuple[Outfit, ...]
    total: int


def create_confirmed_outfit(
    recommendation: OutfitRecommendation,
    user_id: str,
    conversation_id: str,
) -> Outfit:
    """把已校验的临时推荐转换成可持久化 Outfit。"""

    # uuid5 根据命名空间和业务键生成稳定 UUID
    outfit_id = str(
        uuid5(
            OUTFIT_ID_NAMESPACE,
            f"{user_id}:{conversation_id}",
        ),
    )

    return Outfit(
        outfit_id=outfit_id,
        user_id=user_id,
        name=recommendation.name,
        scenario=recommendation.scenario,
        style_tags=recommendation.style_tags,
        season=recommendation.season,
        items=recommendation.items,
        recommendation_reason=(
            recommendation.recommendation_reason
        ),
        notes=recommendation.notes,
    )


async def save_confirmed_outfit(
    graph: ShoppingGraph,
    repository: OutfitRepository,
    user_id: str,
    conversation_id: str,
) -> Outfit:
    """读取当前用户会话中的推荐并保存。"""

    # thread_id 规则必须与聊天接口保持一致，且包含 user_id 隔离用户
    thread_id = (
        f"user:{user_id}:conversation:{conversation_id}"
    )
    state_snapshot = await graph.aget_state(
        {
            "configurable": {
                "thread_id": thread_id,
            },
        },
    )

    recommendation = state_snapshot.values.get(
        "outfit_recommendation",
    )

    if not isinstance(
        recommendation,
        OutfitRecommendation,
    ):
        raise OutfitRecommendationNotFoundError(
            "当前会话中没有可以保存的穿搭推荐",
        )

    outfit = create_confirmed_outfit(
        recommendation=recommendation,
        user_id=user_id,
        conversation_id=conversation_id,
    )

    # 仓库只执行 flush，事务由请求级数据库 Session 统一提交
    return await repository.save(outfit)


async def list_saved_outfits(
    repository: OutfitRepository,
    user_id: str,
    scenario: str | None = None,
    favorite_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> SavedOutfitPage:
    """列出属于当前用户的已保存穿搭。"""

    outfits = await repository.search(
        user_id=user_id,
        scenario=scenario,
        favorite_only=favorite_only,
        limit=limit,
        offset=offset,
    )
    total = await repository.count(
        user_id=user_id,
        scenario=scenario,
        favorite_only=favorite_only,
    )

    return SavedOutfitPage(
        items=tuple(outfits),
        total=total,
    )


async def get_saved_outfit(
    repository: OutfitRepository,
    user_id: str,
    outfit_id: str,
) -> Outfit:
    """读取当前用户的一套已保存穿搭。"""

    outfit = await repository.get_by_id(
        user_id=user_id,
        outfit_id=outfit_id,
    )

    if outfit is None:
        # 对不存在和属于其他用户的 ID 返回相同结果，避免泄露数据
        raise OutfitNotFoundError(
            "未找到指定的穿搭方案",
        )

    return outfit


async def update_outfit_favorite(
    repository: OutfitRepository,
    user_id: str,
    outfit_id: str,
    is_favorite: bool,
) -> Outfit:
    """更新当前用户已保存穿搭的收藏状态。"""

    outfit = await get_saved_outfit(
        repository=repository,
        user_id=user_id,
        outfit_id=outfit_id,
    )

    # Outfit 使用 frozen=True，通过复制产生新的不可变领域对象
    updated_outfit = outfit.model_copy(
        update={
            "is_favorite": is_favorite,
        },
    )

    return await repository.save(
        updated_outfit,
    )
