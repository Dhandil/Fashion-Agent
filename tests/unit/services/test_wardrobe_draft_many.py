"""同一张照片识别多件衣物的应用服务测试。"""

from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import WardrobeVisionProviderError
from app.domain.entities.wardrobe_draft import WardrobeItemRecognition
from app.domain.entities.wardrobe_image import (
    WardrobeImage,
    WardrobeImageContentType,
)
from app.domain.providers.wardrobe_vision import WardrobeImageMultiRecognizer
from app.services.wardrobe_draft import recognize_wardrobe_image_content_many


@pytest.mark.anyio
async def test_recognition_many_creates_independent_drafts() -> None:
    """验证一张照片中的多个识别结果会变成多个独立草稿。"""

    recognizer = AsyncMock(spec=WardrobeImageMultiRecognizer)
    recognizer.recognize_many.return_value = (
        WardrobeItemRecognition(
            name="浅蓝色衬衫",
            category="衬衫",
            confidence=0.9,
        ),
        WardrobeItemRecognition(
            name="深灰色长裤",
            category="长裤",
            confidence=0.8,
        ),
    )
    image = WardrobeImage(
        content=b"\xff\xd8\xff" + b"multi-garment",
        content_type=WardrobeImageContentType.JPEG,
    )

    drafts = await recognize_wardrobe_image_content_many(
        recognizer=recognizer,
        user_id="multi-user",
        image=image,
        max_image_bytes=1024,
        min_confidence=0.6,
        image_asset_id="asset-shared",
    )

    assert [draft.category for draft in drafts] == ["衬衫", "长裤"]
    assert len({draft.draft_id for draft in drafts}) == 2
    assert all(draft.image_asset_id == "asset-shared" for draft in drafts)
    recognizer.recognize_many.assert_awaited_once()


@pytest.mark.anyio
@pytest.mark.parametrize("recognitions", [(), tuple(
    WardrobeItemRecognition(
        name=f"衣物{i}",
        category="上衣",
        confidence=0.8,
    )
    for i in range(3)
)])
async def test_recognition_many_rejects_empty_or_excessive_results(
    recognitions: tuple[WardrobeItemRecognition, ...],
) -> None:
    """验证空结果和超过上限的结果不会静默返回。"""

    recognizer = AsyncMock(spec=WardrobeImageMultiRecognizer)
    recognizer.recognize_many.return_value = recognitions
    image = WardrobeImage(
        content=b"\xff\xd8\xff" + b"multi-garment",
        content_type=WardrobeImageContentType.JPEG,
    )

    with pytest.raises(WardrobeVisionProviderError):
        await recognize_wardrobe_image_content_many(
            recognizer=recognizer,
            user_id="multi-user",
            image=image,
            max_image_bytes=1024,
            min_confidence=0.6,
            max_detected_items=2,
        )
