"""用户衣橱 API 路由。"""

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Annotated
from uuid import uuid4

from fastapi import (
    APIRouter,
    Query,
    Request,
    Response,
    status,
)

from app.api.dependencies.database import (
    FashionRepositoriesDependency,
)
from app.api.dependencies.identity import (
    CurrentUserDependency,
    SettingsDependency,
)
from app.api.dependencies.storage import WardrobeImageStorageDependency
from app.api.dependencies.vision import (
    WardrobeImageRecognizerDependency,
)
from app.api.schemas.wardrobe import (
    WardrobeImageAssetResponse,
    WardrobeImageBatchRecognitionFailure,
    WardrobeImageBatchRecognitionRequest,
    WardrobeImageBatchRecognitionResponse,
    WardrobeImageRecognitionRequest,
    WardrobeImageUploadRequest,
    WardrobeImageUploadResponse,
    WardrobeItemCreate,
    WardrobeItemDraftResponse,
    WardrobeItemListResponse,
    WardrobeItemPatch,
    WardrobeItemResponse,
    WardrobeItemStatusUpdate,
)
from app.core.exceptions import (
    FashionAgentError,
    WardrobeImageAssetNotFoundError,
    WardrobeImageError,
    WardrobeImageStorageError,
    WardrobeVisionProviderError,
)
from app.domain.entities.wardrobe_image import WardrobeImage
from app.domain.entities.wardrobe_image_asset import (
    WardrobeImageAsset,
    WardrobeImageAssetStatus,
)
from app.domain.entities.wardrobe_item import (
    WardrobeItem,
    WardrobeItemStatus,
)
from app.domain.policies.wardrobe_image import validate_wardrobe_image
from app.domain.repositories.wardrobe_image_asset import (
    WardrobeImageAssetRepository,
)
from app.services.wardrobe import (
    delete_wardrobe_item,
    get_wardrobe_item,
    list_wardrobe_items,
    update_wardrobe_item,
)
from app.services.wardrobe_draft import (
    recognize_wardrobe_image,
    recognize_wardrobe_image_content,
    recognize_wardrobe_image_content_many,
)
from app.services.wardrobe_image_assets import (
    discard_unattached_wardrobe_image_asset,
    mark_wardrobe_image_asset_deletion_pending,
)

router = APIRouter(
    prefix="/wardrobe",
    tags=["wardrobe"],
)


def _image_content_url(image_asset_id: str) -> str:
    """生成需要当前用户身份才能访问的图片地址。"""

    return f"/api/v1/wardrobe/images/{image_asset_id}/content"


def _get_image_asset_repository(
    repositories: FashionRepositoriesDependency,
) -> WardrobeImageAssetRepository:
    """取得图片资产仓库；旧的非图片测试装配会明确失败。"""

    if repositories.wardrobe_image_assets is None:
        raise WardrobeImageError("图片资产存储尚未配置。")
    return repositories.wardrobe_image_assets


@router.post(
    "/images/uploads",
    response_model=WardrobeImageUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建本地图片上传凭证",
)
async def create_wardrobe_image_upload(
    request: WardrobeImageUploadRequest,
    current_user: CurrentUserDependency,
    repositories: FashionRepositoriesDependency,
    settings: SettingsDependency,
) -> WardrobeImageUploadResponse:
    """创建短时上传地址；图片尚未写入文件卷。"""

    if request.byte_size > settings.wardrobe_image_max_bytes:
        raise WardrobeImageError(
            f"衣物照片超过 {settings.wardrobe_image_max_bytes} 字节上限，请压缩后重试。",
        )

    image_asset_id = str(uuid4())
    extension = ".jpg" if request.content_type.value == "image/jpeg" else ".png"
    now = datetime.now(UTC)
    expires_at = now + timedelta(
        seconds=settings.wardrobe_image_upload_ttl_seconds,
    )
    asset = WardrobeImageAsset(
        image_asset_id=image_asset_id,
        user_id=current_user.user_id,
        object_key=f"{image_asset_id}{extension}",
        content_type=request.content_type,
        byte_size=0,
        status=WardrobeImageAssetStatus.PENDING,
        created_at=now,
        expires_at=expires_at,
    )
    await _get_image_asset_repository(repositories).save(asset)
    content_url = _image_content_url(image_asset_id)
    return WardrobeImageUploadResponse(
        image_asset_id=image_asset_id,
        upload_url=content_url,
        content_url=content_url,
        expires_at=expires_at,
    )


@router.put(
    "/images/{image_asset_id}/content",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="直传衣物图片到本地文件卷",
)
async def upload_wardrobe_image_content(
    image_asset_id: str,
    request: Request,
    current_user: CurrentUserDependency,
    repositories: FashionRepositoriesDependency,
    settings: SettingsDependency,
    storage: WardrobeImageStorageDependency,
) -> Response:
    """接收前端直传的原始图片字节，并原子写入本地文件卷。"""

    asset = await _get_image_asset_repository(repositories).get_by_id(
        current_user.user_id,
        image_asset_id,
    )
    if asset is None:
        raise WardrobeImageAssetNotFoundError("图片资产不存在。")
    if asset.status is not WardrobeImageAssetStatus.PENDING:
        raise WardrobeImageError("图片上传凭证已使用或已过期。")
    if datetime.now(UTC) > asset.expires_at:
        raise WardrobeImageError("图片上传凭证已过期，请重新选择图片。")

    content = await request.body()
    image = WardrobeImage(content=content, content_type=asset.content_type)
    validate_wardrobe_image(
        image=image,
        max_bytes=settings.wardrobe_image_max_bytes,
    )
    storage.write(asset.object_key, content)
    uploaded_asset = asset.model_copy(
        update={
            "byte_size": len(content),
            "sha256": sha256(content).hexdigest(),
            "status": WardrobeImageAssetStatus.UPLOADED,
        },
    )
    await _get_image_asset_repository(repositories).save(uploaded_asset)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/images/{image_asset_id}/complete",
    response_model=WardrobeImageAssetResponse,
    summary="确认衣物图片上传完成",
)
async def complete_wardrobe_image_upload(
    image_asset_id: str,
    current_user: CurrentUserDependency,
    repositories: FashionRepositoriesDependency,
    storage: WardrobeImageStorageDependency,
) -> WardrobeImageAssetResponse:
    """确认元数据与文件卷状态一致后，允许进入识别流程。"""

    asset = await _get_image_asset_repository(repositories).get_by_id(
        current_user.user_id,
        image_asset_id,
    )
    if asset is None:
        raise WardrobeImageAssetNotFoundError("图片资产不存在。")
    if asset.status is not WardrobeImageAssetStatus.UPLOADED or not asset.sha256:
        raise WardrobeImageError("图片尚未完成上传。")
    if not storage.exists(asset.object_key):
        raise WardrobeImageError("图片文件不存在，请重新上传。")

    return WardrobeImageAssetResponse(
        image_asset_id=asset.image_asset_id,
        content_type=asset.content_type,
        byte_size=asset.byte_size,
        sha256=asset.sha256,
        status=asset.status.value,
        content_url=_image_content_url(asset.image_asset_id),
    )


@router.delete(
    "/images/{image_asset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="丢弃未关联的衣物图片",
)
async def discard_wardrobe_image_asset(
    image_asset_id: str,
    current_user: CurrentUserDependency,
    repositories: FashionRepositoriesDependency,
    storage: WardrobeImageStorageDependency,
) -> Response:
    """清理用户取消或识别失败后仍未关联衣橱单品的图片。"""

    await discard_unattached_wardrobe_image_asset(
        repository=_get_image_asset_repository(repositories),
        storage=storage,
        user_id=current_user.user_id,
        image_asset_id=image_asset_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/images/{image_asset_id}/content",
    summary="读取当前用户的衣物图片",
)
async def read_wardrobe_image_content(
    image_asset_id: str,
    current_user: CurrentUserDependency,
    repositories: FashionRepositoriesDependency,
    storage: WardrobeImageStorageDependency,
) -> Response:
    """按用户隔离读取图片，用于本地开发预览。"""

    asset = await _get_image_asset_repository(repositories).get_by_id(
        current_user.user_id,
        image_asset_id,
    )
    if asset is None or asset.status not in {
        WardrobeImageAssetStatus.UPLOADED,
        WardrobeImageAssetStatus.ATTACHED,
    }:
        raise WardrobeImageAssetNotFoundError("图片资产不存在。")
    return Response(
        content=storage.read(asset.object_key),
        media_type=asset.content_type.value,
        headers={"Cache-Control": "private, max-age=600"},
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
    response_items = tuple(WardrobeItemResponse.model_validate(item) for item in page.items)

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

    image_asset = None
    if request.image_asset_id is not None:
        image_asset = await _get_image_asset_repository(repositories).get_by_id(
            current_user.user_id,
            request.image_asset_id,
        )
        if image_asset is None or image_asset.status not in {
            WardrobeImageAssetStatus.UPLOADED,
            WardrobeImageAssetStatus.ATTACHED,
        }:
            raise WardrobeImageAssetNotFoundError("图片资产不存在或尚未完成上传。")

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

    if image_asset is not None:
        await _get_image_asset_repository(repositories).save(
            image_asset.model_copy(
                update={
                    "status": WardrobeImageAssetStatus.ATTACHED,
                    "attached_at": datetime.now(UTC),
                },
            ),
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
    repositories: FashionRepositoriesDependency,
    recognizer: WardrobeImageRecognizerDependency,
    settings: SettingsDependency,
    storage: WardrobeImageStorageDependency,
) -> WardrobeItemDraftResponse:
    """识别照片中的衣物特征，结果需要用户确认后才能写入衣橱。"""

    # 本接口不访问衣橱仓库；图片资产只在用户确认后才成为衣橱事实
    if request.image_asset_id is not None:
        asset = await _get_image_asset_repository(repositories).get_by_id(
            current_user.user_id,
            request.image_asset_id,
        )
        if asset is None or asset.status not in {
            WardrobeImageAssetStatus.UPLOADED,
            WardrobeImageAssetStatus.ATTACHED,
        }:
            raise WardrobeImageAssetNotFoundError("图片资产不存在或尚未完成上传。")
        image = WardrobeImage(
            content=storage.read(asset.object_key),
            content_type=asset.content_type,
        )
        draft = await recognize_wardrobe_image_content(
            recognizer=recognizer,
            user_id=current_user.user_id,
            image=image,
            max_image_bytes=settings.wardrobe_image_max_bytes,
            min_confidence=settings.wardrobe_draft_min_confidence,
            image_url=_image_content_url(asset.image_asset_id),
            image_asset_id=asset.image_asset_id,
            hint=request.hint,
        )
    else:
        # 兼容旧客户端的 Base64 请求
        if request.content_type is None:
            raise WardrobeImageError(
                "使用 Base64 图片时必须提供 content_type",
            )
        draft = await recognize_wardrobe_image(
            recognizer=recognizer,
            user_id=current_user.user_id,
            image_base64=request.image_base64 or "",
            content_type=request.content_type,
            max_image_bytes=settings.wardrobe_image_max_bytes,
            min_confidence=settings.wardrobe_draft_min_confidence,
            image_url=request.image_url,
            hint=request.hint,
        )

    return WardrobeItemDraftResponse.model_validate(
        draft,
    )


@router.post(
    "/recognitions/batch",
    response_model=WardrobeImageBatchRecognitionResponse,
    summary="批量识别衣物图片",
)
async def recognize_wardrobe_item_images(
    request: WardrobeImageBatchRecognitionRequest,
    current_user: CurrentUserDependency,
    repositories: FashionRepositoriesDependency,
    recognizer: WardrobeImageRecognizerDependency,
    settings: SettingsDependency,
    storage: WardrobeImageStorageDependency,
) -> WardrobeImageBatchRecognitionResponse:
    """逐张读取已上传图片；单张失败不会阻断同批其他结果。"""

    items: list[WardrobeItemDraftResponse] = []
    failures: list[WardrobeImageBatchRecognitionFailure] = []
    image_assets = _get_image_asset_repository(repositories)

    for image_asset_id in request.image_asset_ids:
        try:
            asset = await image_assets.get_by_id(
                current_user.user_id,
                image_asset_id,
            )
            if asset is None or asset.status not in {
                WardrobeImageAssetStatus.UPLOADED,
                WardrobeImageAssetStatus.ATTACHED,
            }:
                raise WardrobeImageAssetNotFoundError(
                    "图片资产不存在或尚未完成上传。",
                )

            image = WardrobeImage(
                content=storage.read(asset.object_key),
                content_type=asset.content_type,
            )
            drafts = await recognize_wardrobe_image_content_many(
                recognizer=recognizer,
                user_id=current_user.user_id,
                image=image,
                max_image_bytes=settings.wardrobe_image_max_bytes,
                min_confidence=settings.wardrobe_draft_min_confidence,
                max_detected_items=settings.wardrobe_image_max_detected_items,
                image_url=_image_content_url(asset.image_asset_id),
                image_asset_id=asset.image_asset_id,
                hint=request.hint,
            )
            items.extend(
                WardrobeItemDraftResponse.model_validate(draft)
                for draft in drafts
            )
        except FashionAgentError as exc:
            if isinstance(exc, WardrobeImageAssetNotFoundError):
                code = "image_asset_not_found"
            elif isinstance(exc, WardrobeImageStorageError):
                code = "image_storage_error"
            elif isinstance(exc, WardrobeVisionProviderError):
                code = "wardrobe_vision_error"
            else:
                code = "wardrobe_image_invalid"
            failures.append(
                WardrobeImageBatchRecognitionFailure(
                    image_asset_id=image_asset_id,
                    code=code,
                    message="该图片识别失败，请稍后重试或手动录入。",
                ),
            )

    return WardrobeImageBatchRecognitionResponse(
        items=tuple(items),
        failures=tuple(failures),
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

    item = await get_wardrobe_item(
        repository=repositories.wardrobe,
        user_id=current_user.user_id,
        wardrobe_item_id=wardrobe_item_id,
    )

    # 在同一个请求事务中先记录图片待清理状态，再删除衣橱事实。
    if item.image_asset_id is not None:
        await mark_wardrobe_image_asset_deletion_pending(
            repository=_get_image_asset_repository(repositories),
            user_id=current_user.user_id,
            image_asset_id=item.image_asset_id,
        )

    await delete_wardrobe_item(
        repository=repositories.wardrobe,
        user_id=current_user.user_id,
        wardrobe_item_id=wardrobe_item_id,
    )
