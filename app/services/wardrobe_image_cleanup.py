"""衣物图片资产生命周期清理服务。"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.core.exceptions import WardrobeImageStorageError
from app.domain.entities.wardrobe_image_asset import (
    WardrobeImageAssetStatus,
)
from app.domain.providers.image_storage import WardrobeImageStorage
from app.domain.repositories.wardrobe_image_asset import (
    WardrobeImageAssetRepository,
)


@dataclass(frozen=True, slots=True)
class WardrobeImageCleanupResult:
    """一次清理批次的统计结果。"""

    candidate_count: int
    deleted_count: int
    failed_count: int


async def cleanup_wardrobe_image_assets(
    repository: WardrobeImageAssetRepository,
    storage: WardrobeImageStorage,
    *,
    now: datetime | None = None,
    orphan_retention: timedelta = timedelta(hours=24),
    deletion_retention: timedelta = timedelta(days=7),
    limit: int | None = 100,
    dry_run: bool = False,
) -> WardrobeImageCleanupResult:
    """清理过期、孤儿和已进入删除保留期的图片资产。

    清理操作可以重复执行：文件不存在时存储适配器应视为删除成功，
    只有文件卷操作失败才保留资产状态，等待下一次重试。
    """

    cleanup_time = now or datetime.now(UTC)
    candidates = await repository.list_cleanup_candidates(
        now=cleanup_time,
        orphan_uploaded_before=cleanup_time - orphan_retention,
        deletion_pending_before=cleanup_time - deletion_retention,
        limit=limit,
    )

    if dry_run:
        return WardrobeImageCleanupResult(
            candidate_count=len(candidates),
            deleted_count=0,
            failed_count=0,
        )

    deleted_count = 0
    failed_count = 0
    for asset in candidates:
        try:
            storage.delete(asset.object_key)
        except WardrobeImageStorageError:
            # 保留原状态以便下一次清理任务重试。
            failed_count += 1
            continue

        await repository.save(
            asset.model_copy(
                update={
                    "status": WardrobeImageAssetStatus.DELETED,
                    "deleted_at": cleanup_time,
                },
            ),
        )
        deleted_count += 1

    return WardrobeImageCleanupResult(
        candidate_count=len(candidates),
        deleted_count=deleted_count,
        failed_count=failed_count,
    )
