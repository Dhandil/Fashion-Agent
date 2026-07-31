"""用户穿搭方案 API 路由。"""

from fastapi import (
    APIRouter,
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
    OutfitResponse,
)
from app.services.outfit import save_confirmed_outfit

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
