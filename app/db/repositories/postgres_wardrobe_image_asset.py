"""PostgreSQL 衣物图片资产元数据仓库。"""

from datetime import datetime

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.wardrobe_image_asset import WardrobeImageAssetModel
from app.domain.entities.wardrobe_image import WardrobeImageContentType
from app.domain.entities.wardrobe_image_asset import (
    WardrobeImageAsset,
    WardrobeImageAssetStatus,
)


def _to_entity(model: WardrobeImageAssetModel) -> WardrobeImageAsset:
    return WardrobeImageAsset(
        image_asset_id=model.image_asset_id,
        user_id=model.user_id,
        object_key=model.object_key,
        content_type=WardrobeImageContentType(model.content_type),
        byte_size=model.byte_size,
        sha256=model.sha256,
        status=WardrobeImageAssetStatus(model.status),
        created_at=model.created_at,
        expires_at=model.expires_at,
        attached_at=model.attached_at,
        deleted_at=model.deleted_at,
    )


class PostgresWardrobeImageAssetRepository:
    """使用请求级 Session 保存图片资产元数据。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, asset: WardrobeImageAsset) -> WardrobeImageAsset:
        await self._session.merge(
            WardrobeImageAssetModel(
                user_id=asset.user_id,
                image_asset_id=asset.image_asset_id,
                object_key=asset.object_key,
                content_type=asset.content_type.value,
                byte_size=asset.byte_size,
                sha256=asset.sha256,
                status=asset.status.value,
                created_at=asset.created_at,
                expires_at=asset.expires_at,
                attached_at=asset.attached_at,
                deleted_at=asset.deleted_at,
            ),
        )
        await self._session.flush()
        return asset

    async def get_by_id(
        self,
        user_id: str,
        image_asset_id: str,
    ) -> WardrobeImageAsset | None:
        result = await self._session.execute(
            select(WardrobeImageAssetModel).where(
                WardrobeImageAssetModel.user_id == user_id,
                WardrobeImageAssetModel.image_asset_id == image_asset_id,
            ),
        )
        model = result.scalar_one_or_none()
        return None if model is None else _to_entity(model)

    async def list_cleanup_candidates(
        self,
        now: datetime,
        orphan_uploaded_before: datetime,
        deletion_pending_before: datetime,
    ) -> tuple[WardrobeImageAsset, ...]:
        """查询需要由清理服务处理的图片资产。"""

        result = await self._session.execute(
            select(WardrobeImageAssetModel).where(
                or_(
                    and_(
                        WardrobeImageAssetModel.status == WardrobeImageAssetStatus.PENDING.value,
                        WardrobeImageAssetModel.expires_at <= now,
                    ),
                    and_(
                        WardrobeImageAssetModel.status == WardrobeImageAssetStatus.UPLOADED.value,
                        WardrobeImageAssetModel.attached_at.is_(None),
                        WardrobeImageAssetModel.created_at <= orphan_uploaded_before,
                    ),
                    and_(
                        WardrobeImageAssetModel.status
                        == WardrobeImageAssetStatus.DELETION_PENDING.value,
                        WardrobeImageAssetModel.deleted_at.is_not(None),
                        WardrobeImageAssetModel.deleted_at <= deletion_pending_before,
                    ),
                ),
            ),
        )
        return tuple(_to_entity(model) for model in result.scalars().all())
