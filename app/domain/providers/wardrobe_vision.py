"""衣物照片识别外部能力接口。"""

from typing import Protocol

from app.domain.entities.wardrobe_draft import (
    WardrobeItemRecognition,
)
from app.domain.entities.wardrobe_image import WardrobeImage


class WardrobeImageRecognizer(Protocol):
    """定义视觉模型或 MCP 适配器必须提供的能力。"""

    async def recognize(
        self,
        image: WardrobeImage,
        hint: str | None = None,
    ) -> WardrobeItemRecognition:
        """识别一张衣物照片，返回等待用户确认的候选特征。"""

        ...
