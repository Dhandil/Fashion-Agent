"""衣物图片资产状态转换服务。"""

from datetime import UTC, datetime

from app.core.exceptions import WardrobeImageAssetNotFoundError
from app.domain.entities.wardrobe_image_asset import (
    WardrobeImageAsset,
    WardrobeImageAssetStatus,
)
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
