"""衣物图片存储 Provider 工厂。"""

from functools import lru_cache

from app.core.config import get_settings
from app.domain.providers.image_storage import WardrobeImageStorage
from app.integrations.storage.local import LocalWardrobeImageStorage


@lru_cache
def get_wardrobe_image_storage() -> WardrobeImageStorage:
    """创建本地文件卷存储，后续可替换为 S3-compatible 实现。"""

    settings = get_settings()
    return LocalWardrobeImageStorage(settings.wardrobe_image_storage_directory)
