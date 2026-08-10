"""衣物图片资产领域实体。"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.domain.entities.wardrobe_image import WardrobeImageContentType


class WardrobeImageAssetStatus(StrEnum):
    """图片资产在本地文件卷中的生命周期状态。"""

    PENDING = "pending"
    UPLOADED = "uploaded"
    ATTACHED = "attached"
    DELETION_PENDING = "deletion_pending"
    DELETED = "deleted"


class WardrobeImageAsset(BaseModel):
    """图片文件与用户、衣橱业务之间的持久化元数据。"""

    image_asset_id: str = Field(min_length=1, max_length=100)
    user_id: str = Field(min_length=1, max_length=100)
    object_key: str = Field(min_length=1, max_length=500)
    content_type: WardrobeImageContentType
    byte_size: int = Field(ge=0)
    sha256: str | None = Field(default=None, min_length=64, max_length=64)
    status: WardrobeImageAssetStatus = WardrobeImageAssetStatus.PENDING
    created_at: datetime
    expires_at: datetime
    attached_at: datetime | None = None
    deleted_at: datetime | None = None

    model_config = ConfigDict(frozen=True)
