"""衣物图片资产仓库接口。"""

from datetime import datetime
from typing import Protocol

from app.domain.entities.wardrobe_image_asset import WardrobeImageAsset


class WardrobeImageAssetRepository(Protocol):
    """保存用户隔离的图片元数据，不负责实际文件读写。"""

    async def save(self, asset: WardrobeImageAsset) -> WardrobeImageAsset:
        ...

    async def get_by_id(
        self,
        user_id: str,
        image_asset_id: str,
    ) -> WardrobeImageAsset | None:
        ...

    async def list_cleanup_candidates(
        self,
        now: datetime,
        orphan_uploaded_before: datetime,
        deletion_pending_before: datetime,
        limit: int | None = None,
    ) -> tuple[WardrobeImageAsset, ...]:
        """查询已过期、长期未关联或等待删除的图片资产。"""
        ...
