"""衣物图片资产状态转换服务。"""

from datetime import UTC, datetime

from app.core.exceptions import (
    WardrobeImageAssetNotFoundError,
    WardrobeImageError,
)
from app.domain.entities.wardrobe_image_asset import (
    WardrobeImageAsset,
    WardrobeImageAssetStatus,
)
from app.domain.providers.image_storage import WardrobeImageStorage
from app.domain.repositories.wardrobe_image_asset import (
    WardrobeImageAssetRepository,
)


async def mark_wardrobe_image_asset_deletion_pending(
    repository: WardrobeImageAssetRepository,
    user_id: str,
    image_asset_id: str,
    *,
    now: datetime | None = None,
) -> WardrobeImageAsset:
    """将衣橱删除时关联的图片标记为待清理。"""

    asset = await repository.get_by_id(user_id, image_asset_id)
    if asset is None:
        raise WardrobeImageAssetNotFoundError("关联的衣物图片资产不存在")

    if asset.status in {
        WardrobeImageAssetStatus.DELETION_PENDING,
        WardrobeImageAssetStatus.DELETED,
    }:
        return asset

    deletion_time = now or datetime.now(UTC)
    return await repository.save(
        asset.model_copy(
            update={
                "status": WardrobeImageAssetStatus.DELETION_PENDING,
                "deleted_at": deletion_time,
            },
        ),
    )


async def discard_unattached_wardrobe_image_asset(
    repository: WardrobeImageAssetRepository,
    storage: WardrobeImageStorage,
    user_id: str,
    image_asset_id: str,
    *,
    now: datetime | None = None,
) -> WardrobeImageAsset:
    """立即丢弃尚未关联衣橱单品的图片资产。

    该操作用于用户取消识别或识别失败后的清理。已经关联衣橱单品的图片
    不能通过这个接口删除，必须先删除对应的衣橱事实并进入保留期清理。
    """

    asset = await repository.get_by_id(user_id, image_asset_id)
    if asset is None:
        raise WardrobeImageAssetNotFoundError("图片资产不存在。")
    if asset.status is WardrobeImageAssetStatus.ATTACHED:
        raise WardrobeImageError("图片已经关联衣橱单品，不能直接丢弃。")
    if asset.status is WardrobeImageAssetStatus.DELETED:
        return asset

    if asset.status is not WardrobeImageAssetStatus.PENDING:
        storage.delete(asset.object_key)

    discarded_at = now or datetime.now(UTC)
    return await repository.save(
        asset.model_copy(
            update={
                "status": WardrobeImageAssetStatus.DELETED,
                "deleted_at": discarded_at,
            },
        ),
    )
