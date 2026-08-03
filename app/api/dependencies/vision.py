"""衣物照片识别服务依赖。"""

from typing import Annotated

from fastapi import Depends

from app.domain.providers.wardrobe_vision import (
    WardrobeImageRecognizer,
)
from app.integrations.vision.provider import (
    get_wardrobe_image_recognizer,
)

# Provider 可以关闭；关闭时照片识别接口明确返回未启用，不做静默降级
WardrobeImageRecognizerDependency = Annotated[
    WardrobeImageRecognizer | None,
    Depends(get_wardrobe_image_recognizer),
]
