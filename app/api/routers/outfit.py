"""用户穿搭方案 API 路由。"""

from typing import Annotated

from fastapi import (
    APIRouter,
    Query,
    status,
)

from app.api.dependencies.agent import (
    RequestShoppingGraph,
)
from app.api.dependencies.database import (
    FashionRepositoriesDependency,
)
from app.api.dependencies.identity import (
    CurrentUserDependency,
)
from app.api.schemas.outfit import (
    OutfitConfirmRequest,
    OutfitFavoriteUpdate,
    OutfitListResponse,
    OutfitResponse,
)
from app.services.outfit import (
    get_saved_outfit,
    list_saved_outfits,
    save_confirmed_outfit,
    update_outfit_favorite,
)

router = APIRouter(
    prefix="/outfits",
    tags=["outfits"],
)


@router.post(
    "",
    response_model=OutfitResponse,
    status_code=status.HTTP_201_CREATED,
    summary="确认并保存当前穿搭推荐",
)
async def confirm_outfit(
    request: OutfitConfirmRequest,
    current_user: CurrentUserDependency,
    graph: RequestShoppingGraph,
    repositories: FashionRepositoriesDependency,
) -> OutfitResponse:
    """保存当前用户指定会话中的最后一套结构化推荐。"""

    saved_outfit = await save_confirmed_outfit(
        graph=graph,
        repository=repositories.outfits,
        user_id=current_user.user_id,
        conversation_id=request.conversation_id,
    )

    return OutfitResponse.model_validate(
        saved_outfit,
    )


@router.get(
    "",
    response_model=OutfitListResponse,
    summary="查询当前用户保存的穿搭",
)
async def list_outfits(
    current_user: CurrentUserDependency,
    repositories: FashionRepositoriesDependency,
    scenario: Annotated[
        str | None,
        Query(
            min_length=1,
            max_length=100,
        ),
    ] = None,
    favorite_only: Annotated[
        bool,
        Query(),
    ] = False,
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=100,
        ),
    ] = 50,
) -> OutfitListResponse:
    """根据当前用户和可选条件查询已保存穿搭。"""

    outfits = await list_saved_outfits(
        repository=repositories.outfits,
        user_id=current_user.user_id,
        scenario=scenario,
        favorite_only=favorite_only,
        limit=limit,
    )

    response_items = tuple(
        OutfitResponse.model_validate(outfit)
        for outfit in outfits
    )

    return OutfitListResponse(
        items=response_items,
        count=len(response_items),
    )


@router.get(
    "/{outfit_id}",
    response_model=OutfitResponse,
    summary="查询已保存穿搭详情",
)
async def get_outfit(
    outfit_id: str,
    current_user: CurrentUserDependency,
    repositories: FashionRepositoriesDependency,
) -> OutfitResponse:
    """读取当前用户指定 ID 的穿搭方案。"""

    outfit = await get_saved_outfit(
        repository=repositories.outfits,
        user_id=current_user.user_id,
        outfit_id=outfit_id,
    )

    return OutfitResponse.model_validate(
        outfit,
    )


@router.patch(
    "/{outfit_id}/favorite",
    response_model=OutfitResponse,
    summary="修改穿搭收藏状态",
)
async def set_outfit_favorite(
    outfit_id: str,
    request: OutfitFavoriteUpdate,
    current_user: CurrentUserDependency,
    repositories: FashionRepositoriesDependency,
) -> OutfitResponse:
    """收藏或取消收藏当前用户的一套穿搭。"""

    updated_outfit = await update_outfit_favorite(
        repository=repositories.outfits,
        user_id=current_user.user_id,
        outfit_id=outfit_id,
        is_favorite=request.is_favorite,
    )

    return OutfitResponse.model_validate(
        updated_outfit,
    )
