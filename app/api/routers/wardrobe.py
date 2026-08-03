"""用户衣橱 API 路由。"""

from typing import Annotated
from uuid import uuid4

from fastapi import (
    APIRouter,
    Query,
    status,
)

from app.api.dependencies.database import (
    FashionRepositoriesDependency,
)
from app.api.dependencies.identity import (
    CurrentUserDependency,
    SettingsDependency,
)
from app.api.dependencies.vision import (
    WardrobeImageRecognizerDependency,
)
from app.api.schemas.wardrobe import (
    WardrobeImageRecognitionRequest,
    WardrobeItemCreate,
    WardrobeItemDraftResponse,
    WardrobeItemListResponse,
    WardrobeItemPatch,
    WardrobeItemResponse,
    WardrobeItemStatusUpdate,
)
from app.domain.entities.wardrobe_item import (
    WardrobeItem,
    WardrobeItemStatus,
)
from app.services.wardrobe import (
    delete_wardrobe_item,
    get_wardrobe_item,
    list_wardrobe_items,
    update_wardrobe_item,
)
from app.services.wardrobe_draft import (
    recognize_wardrobe_image,
)

router = APIRouter(
    prefix="/wardrobe",
    tags=["wardrobe"],
)


@router.get(
    "",
    response_model=WardrobeItemListResponse,
    summary="查询当前用户衣橱",
)
async def list_current_user_wardrobe(
    current_user: CurrentUserDependency,
    repositories: FashionRepositoriesDependency,
    category: Annotated[
        str | None,
        Query(
            min_length=1,
            max_length=100,
        ),
    ] = None,
    item_status: Annotated[
        WardrobeItemStatus | None,
        Query(
            alias="status",
        ),
    ] = None,
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
) -> WardrobeItemListResponse:
    """根据品类、状态和分页条件查询当前用户衣橱。"""

    page = await list_wardrobe_items(
        repository=repositories.wardrobe,
        user_id=current_user.user_id,
        category=category,
        status=item_status,
        limit=limit,
        offset=offset,
    )
    response_items = tuple(
        WardrobeItemResponse.model_validate(item)
        for item in page.items
    )

    return WardrobeItemListResponse(
        items=response_items,
        count=len(response_items),
        total=page.total,
        limit=limit,
        offset=offset,
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


@router.post(
    "/recognitions",
    response_model=WardrobeItemDraftResponse,
    summary="识别衣物照片并生成待确认草稿",
)
async def recognize_wardrobe_item_image(
    request: WardrobeImageRecognitionRequest,
    current_user: CurrentUserDependency,
    recognizer: WardrobeImageRecognizerDependency,
    settings: SettingsDependency,
) -> WardrobeItemDraftResponse:
    """识别照片中的衣物特征，结果需要用户确认后才能写入衣橱。"""

    # 本接口不访问衣橱仓库，识别结果不会成为永久衣橱事实
    draft = await recognize_wardrobe_image(
        recognizer=recognizer,
        user_id=current_user.user_id,
        image_base64=request.image_base64,
        content_type=request.content_type,
        max_image_bytes=(settings.wardrobe_image_max_bytes),
        min_confidence=(settings.wardrobe_draft_min_confidence),
        image_url=request.image_url,
        hint=request.hint,
    )

    return WardrobeItemDraftResponse.model_validate(
        draft,
    )


@router.get(
    "/{wardrobe_item_id}",
    response_model=WardrobeItemResponse,
    summary="查询衣橱单品详情",
)
async def read_wardrobe_item(
    wardrobe_item_id: str,
    current_user: CurrentUserDependency,
    repositories: FashionRepositoriesDependency,
) -> WardrobeItemResponse:
    """读取当前用户指定 ID 的衣橱单品。"""

    item = await get_wardrobe_item(
        repository=repositories.wardrobe,
        user_id=current_user.user_id,
        wardrobe_item_id=wardrobe_item_id,
    )

    return WardrobeItemResponse.model_validate(
        item,
    )


@router.patch(
    "/{wardrobe_item_id}",
    response_model=WardrobeItemResponse,
    summary="局部修改衣橱单品",
)
async def patch_wardrobe_item(
    wardrobe_item_id: str,
    request: WardrobeItemPatch,
    current_user: CurrentUserDependency,
    repositories: FashionRepositoriesDependency,
) -> WardrobeItemResponse:
    """只修改请求中明确提供的衣橱字段。"""

    item = await update_wardrobe_item(
        repository=repositories.wardrobe,
        user_id=current_user.user_id,
        wardrobe_item_id=wardrobe_item_id,
        changes=request.model_dump(
            exclude_unset=True,
        ),
    )

    return WardrobeItemResponse.model_validate(
        item,
    )


@router.patch(
    "/{wardrobe_item_id}/status",
    response_model=WardrobeItemResponse,
    summary="切换衣橱单品可用状态",
)
async def set_wardrobe_item_status(
    wardrobe_item_id: str,
    request: WardrobeItemStatusUpdate,
    current_user: CurrentUserDependency,
    repositories: FashionRepositoriesDependency,
) -> WardrobeItemResponse:
    """明确切换衣物是否可以参与穿搭推荐。"""

    item = await update_wardrobe_item(
        repository=repositories.wardrobe,
        user_id=current_user.user_id,
        wardrobe_item_id=wardrobe_item_id,
        changes={
            "status": request.status,
        },
    )

    return WardrobeItemResponse.model_validate(
        item,
    )


@router.delete(
    "/{wardrobe_item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除衣橱单品",
)
async def remove_wardrobe_item(
    wardrobe_item_id: str,
    current_user: CurrentUserDependency,
    repositories: FashionRepositoriesDependency,
) -> None:
    """删除当前用户指定 ID 的衣橱单品。"""

    await delete_wardrobe_item(
        repository=repositories.wardrobe,
        user_id=current_user.user_id,
        wardrobe_item_id=wardrobe_item_id,
    )
