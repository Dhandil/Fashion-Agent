"""衣物图片存储依赖。"""

from typing import Annotated

from fastapi import Depends

from app.domain.providers.image_storage import WardrobeImageStorage
from app.integrations.storage.provider import get_wardrobe_image_storage

WardrobeImageStorageDependency = Annotated[
    WardrobeImageStorage,
    Depends(get_wardrobe_image_storage),
]
