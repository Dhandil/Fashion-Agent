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
from app.api.schemas.outfit_feedback import (
    OutfitFeedbackListItem,
    OutfitFeedbackListResponse,
    OutfitFeedbackResponse,
    OutfitFeedbackUpsertRequest,
)
from app.domain.entities.outfit_feedback import (
    OutfitFeedbackSentiment,
)
from app.services.outfit import (
    get_saved_outfit,
    list_saved_outfits,
    save_confirmed_outfit,
    update_outfit_favorite,
)
from app.services.outfit_feedback import (
    delete_saved_outfit_feedback,
    get_saved_outfit_feedback,
    list_recent_outfit_feedback,
    save_outfit_feedback,
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
    offset: Annotated[
        int,
        Query(
            ge=0,
            le=100_000,
        ),
    ] = 0,
) -> OutfitListResponse:
    """根据当前用户和可选条件查询已保存穿搭。"""

    page = await list_saved_outfits(
        repository=repositories.outfits,
        user_id=current_user.user_id,
        scenario=scenario,
        favorite_only=favorite_only,
        limit=limit,
        offset=offset,
    )

    response_items = tuple(
        OutfitResponse.model_validate(outfit)
        for outfit in page.items
    )

    return OutfitListResponse(
        items=response_items,
        count=len(response_items),
        total=page.total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/feedback/recent",
    response_model=OutfitFeedbackListResponse,
    summary="查询最近穿搭反馈",
)
async def list_outfit_feedback(
    current_user: CurrentUserDependency,
    repositories: FashionRepositoriesDependency,
    sentiment: Annotated[
        OutfitFeedbackSentiment | None,
        Query(),
    ] = None,
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=100,
        ),
    ] = 20,
) -> OutfitFeedbackListResponse:
    """查询当前用户最近确认的反馈及对应 Outfit 摘要。"""

    summaries = await list_recent_outfit_feedback(
        outfit_repository=repositories.outfits,
        feedback_repository=(
            repositories.outfit_feedback
        ),
        user_id=current_user.user_id,
        sentiment=sentiment,
        limit=limit,
    )
    response_items = tuple(
        OutfitFeedbackListItem(
            outfit_id=summary.feedback.outfit_id,
            outfit_name=summary.outfit.name,
            scenario=summary.outfit.scenario,
            sentiment=summary.feedback.sentiment,
            comment=summary.feedback.comment,
        )
        for summary in summaries
    )

    return OutfitFeedbackListResponse(
        items=response_items,
        count=len(response_items),
        limit=limit,
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


@router.put(
    "/{outfit_id}/feedback",
    response_model=OutfitFeedbackResponse,
    summary="新增或更新穿搭反馈",
)
async def upsert_outfit_feedback(
    outfit_id: str,
    request: OutfitFeedbackUpsertRequest,
    current_user: CurrentUserDependency,
    repositories: FashionRepositoriesDependency,
) -> OutfitFeedbackResponse:
    """保存当前用户对一套已保存穿搭的最新反馈。"""

    feedback = await save_outfit_feedback(
        outfit_repository=repositories.outfits,
        feedback_repository=(
            repositories.outfit_feedback
        ),
        user_id=current_user.user_id,
        outfit_id=outfit_id,
        sentiment=request.sentiment,
        comment=request.comment,
    )

    return OutfitFeedbackResponse.model_validate(
        feedback,
    )


@router.get(
    "/{outfit_id}/feedback",
    response_model=OutfitFeedbackResponse,
    summary="查询穿搭反馈",
)
async def get_outfit_feedback(
    outfit_id: str,
    current_user: CurrentUserDependency,
    repositories: FashionRepositoriesDependency,
) -> OutfitFeedbackResponse:
    """读取当前用户对一套已保存穿搭的反馈。"""

    feedback = await get_saved_outfit_feedback(
        outfit_repository=repositories.outfits,
        feedback_repository=(
            repositories.outfit_feedback
        ),
        user_id=current_user.user_id,
        outfit_id=outfit_id,
    )

    return OutfitFeedbackResponse.model_validate(
        feedback,
    )


@router.delete(
    "/{outfit_id}/feedback",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除穿搭反馈",
)
async def delete_outfit_feedback(
    outfit_id: str,
    current_user: CurrentUserDependency,
    repositories: FashionRepositoriesDependency,
) -> None:
    """撤回当前用户对一套已保存穿搭的反馈。"""

    await delete_saved_outfit_feedback(
        outfit_repository=repositories.outfits,
        feedback_repository=(
            repositories.outfit_feedback
        ),
        user_id=current_user.user_id,
        outfit_id=outfit_id,
    )
