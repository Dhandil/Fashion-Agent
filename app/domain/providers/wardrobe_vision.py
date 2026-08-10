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


class WardrobeImageMultiRecognizer(Protocol):
    """可从一张照片返回多个衣物候选的视觉能力接口。"""

    async def recognize_many(
        self,
        image: WardrobeImage,
        hint: str | None = None,
    ) -> tuple[WardrobeItemRecognition, ...]:
        """识别照片中的多件衣物，每件返回一个候选特征对象。"""

        ...
