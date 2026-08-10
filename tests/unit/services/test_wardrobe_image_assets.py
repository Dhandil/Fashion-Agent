"""衣物图片资产状态转换服务测试。"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import WardrobeImageAssetNotFoundError
from app.domain.entities.wardrobe_image import WardrobeImageContentType
from app.domain.entities.wardrobe_image_asset import (
    WardrobeImageAsset,
    WardrobeImageAssetStatus,
)
from app.domain.repositories.wardrobe_image_asset import (
    WardrobeImageAssetRepository,
)
from app.services.wardrobe_image_assets import (
    mark_wardrobe_image_asset_deletion_pending,
)


def create_attached_asset() -> WardrobeImageAsset:
    """创建已关联图片资产。"""

    return WardrobeImageAsset(
        image_asset_id="asset-001",
        user_id="user-001",
        object_key="asset-001.jpg",
        content_type=WardrobeImageContentType.JPEG,
        byte_size=10,
        sha256="a" * 64,
        status=WardrobeImageAssetStatus.ATTACHED,
        created_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )


@pytest.mark.anyio
async def test_mark_asset_deletion_pending_sets_timestamp() -> None:
    """验证关联图片会进入待清理状态。"""

    repository = AsyncMock(spec=WardrobeImageAssetRepository)
    repository.get_by_id.return_value = create_attached_asset()
    repository.save.side_effect = lambda asset: asset
    deletion_time = datetime(2026, 8, 8, tzinfo=UTC)

    result = await mark_wardrobe_image_asset_deletion_pending(
        repository,
        "user-001",
        "asset-001",
        now=deletion_time,
    )

    assert result.status is WardrobeImageAssetStatus.DELETION_PENDING
    assert result.deleted_at == deletion_time
    repository.save.assert_awaited_once_with(result)


@pytest.mark.anyio
async def test_mark_asset_deletion_pending_is_idempotent() -> None:
    """验证重复处理已进入删除流程的资产不会重复写入。"""

    repository = AsyncMock(spec=WardrobeImageAssetRepository)
    asset = create_attached_asset().model_copy(
        update={"status": WardrobeImageAssetStatus.DELETION_PENDING},
    )
    repository.get_by_id.return_value = asset

    result = await mark_wardrobe_image_asset_deletion_pending(
        repository,
        "user-001",
        "asset-001",
    )

    assert result is asset
    repository.save.assert_not_awaited()


@pytest.mark.anyio
async def test_mark_asset_deletion_pending_rejects_missing_asset() -> None:
    """验证不存在的资产不会被静默忽略。"""

    repository = AsyncMock(spec=WardrobeImageAssetRepository)
    repository.get_by_id.return_value = None

    with pytest.raises(WardrobeImageAssetNotFoundError):
        await mark_wardrobe_image_asset_deletion_pending(
            repository,
            "user-001",
            "missing",
        )
