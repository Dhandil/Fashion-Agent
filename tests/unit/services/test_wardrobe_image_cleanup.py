"""衣物图片资产清理服务测试。"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock

import pytest

from app.core.exceptions import WardrobeImageStorageError
from app.domain.entities.wardrobe_image import WardrobeImageContentType
from app.domain.entities.wardrobe_image_asset import (
    WardrobeImageAsset,
    WardrobeImageAssetStatus,
)
from app.domain.providers.image_storage import WardrobeImageStorage
from app.domain.repositories.wardrobe_image_asset import (
    WardrobeImageAssetRepository,
)
from app.services.wardrobe_image_cleanup import (
    cleanup_wardrobe_image_assets,
)


def create_asset(
    asset_id: str,
    status: WardrobeImageAssetStatus,
) -> WardrobeImageAsset:
    """创建清理服务测试使用的图片资产。"""

    now = datetime.now(UTC)
    return WardrobeImageAsset(
        image_asset_id=asset_id,
        user_id="user-001",
        object_key=f"{asset_id}.jpg",
        content_type=WardrobeImageContentType.JPEG,
        byte_size=10,
        sha256="a" * 64,
        status=status,
        created_at=now - timedelta(days=2),
        expires_at=now - timedelta(days=1),
        deleted_at=(now - timedelta(days=8) if status is WardrobeImageAssetStatus.DELETION_PENDING else None),
    )


@pytest.mark.anyio
async def test_cleanup_marks_candidates_deleted_after_storage_delete() -> None:
    """验证候选资产删除成功后才会更新为 deleted。"""

    repository = AsyncMock(spec=WardrobeImageAssetRepository)
    repository.list_cleanup_candidates.return_value = (
        create_asset("pending", WardrobeImageAssetStatus.PENDING),
        create_asset("orphan", WardrobeImageAssetStatus.UPLOADED),
        create_asset("queued", WardrobeImageAssetStatus.DELETION_PENDING),
    )
    storage = Mock(spec=WardrobeImageStorage)
    cleanup_time = datetime(2026, 8, 8, tzinfo=UTC)

    result = await cleanup_wardrobe_image_assets(
        repository,
        storage,
        now=cleanup_time,
    )

    assert result.candidate_count == 3
    assert result.deleted_count == 3
    assert result.failed_count == 0
    assert storage.delete.call_count == 3
    assert repository.save.await_count == 3
    assert all(
        call.args[0].status is WardrobeImageAssetStatus.DELETED
        for call in repository.save.await_args_list
    )


@pytest.mark.anyio
async def test_cleanup_keeps_asset_when_storage_delete_fails() -> None:
    """验证文件卷删除失败时保留状态，等待下次任务重试。"""

    repository = AsyncMock(spec=WardrobeImageAssetRepository)
    repository.list_cleanup_candidates.return_value = (
        create_asset("failed", WardrobeImageAssetStatus.UPLOADED),
    )
    storage = Mock(spec=WardrobeImageStorage)
    storage.delete.side_effect = WardrobeImageStorageError("卷暂时不可用")

    result = await cleanup_wardrobe_image_assets(
        repository,
        storage,
        now=datetime(2026, 8, 8, tzinfo=UTC),
    )

    assert result.candidate_count == 1
    assert result.deleted_count == 0
    assert result.failed_count == 1
    repository.save.assert_not_awaited()
