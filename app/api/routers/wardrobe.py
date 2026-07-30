"""用户衣橱 API 路由。"""

from uuid import uuid4

from fastapi import (
    APIRouter,
    status,
)

from app.api.dependencies.database import (
    FashionRepositoriesDependency,
)
from app.api.dependencies.identity import (
    CurrentUserDependency,
)
from app.api.schemas.wardrobe import (
    WardrobeItemCreate,
    WardrobeItemResponse,
)
from app.domain.entities.wardrobe_item import (
    WardrobeItem,
)

router = APIRouter(
    prefix="/wardrobe",
    tags=["wardrobe"],
)


@router.post(
    "",
    response_model=WardrobeItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="新增衣橱单品",
)
async def create_wardrobe_item(
    request: WardrobeItemCreate,
    current_user: CurrentUserDependency,
    repositories: FashionRepositoriesDependency,
) -> WardrobeItemResponse:
    """为当前用户新增一件衣橱单品。"""

    # 用户身份只能来自身份依赖，不能由请求体或 LLM 指定
    wardrobe_item = WardrobeItem(
        wardrobe_item_id=str(uuid4()),
        user_id=current_user.user_id,
        **request.model_dump(),
    )

    # 仓库只执行写入和 flush，事务由请求级 Session 统一提交
    saved_item = await repositories.wardrobe.save(
        wardrobe_item,
    )

    return WardrobeItemResponse.model_validate(
        saved_item,
    )
