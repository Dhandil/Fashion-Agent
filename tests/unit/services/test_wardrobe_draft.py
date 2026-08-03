"""衣物照片识别应用服务测试。"""

from base64 import b64encode
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import (
    WardrobeImageError,
    WardrobeVisionProviderError,
    WardrobeVisionUnavailableError,
)
from app.domain.entities.wardrobe_draft import (
    WardrobeItemRecognition,
)
from app.domain.entities.wardrobe_image import (
    WardrobeImageContentType,
)
from app.domain.providers.wardrobe_vision import (
    WardrobeImageRecognizer,
)
from app.services.wardrobe_draft import (
    recognize_wardrobe_image,
)

# 合法 JPEG 文件头，识别 Provider 由测试替身实现
TEST_IMAGE_BYTES = b"\xff\xd8\xff" + b"\x01" * 12
TEST_IMAGE_BASE64 = b64encode(
    TEST_IMAGE_BYTES,
).decode("ascii")


def create_recognizer(
    recognition: WardrobeItemRecognition,
) -> AsyncMock:
    """创建返回固定识别结果的 Provider 替身。"""

    recognizer = AsyncMock(
        spec=WardrobeImageRecognizer,
    )
    recognizer.recognize.return_value = recognition
    return recognizer


@pytest.mark.anyio
async def test_recognition_returns_draft_without_persisting() -> None:
    """验证识别只返回草稿，不产生任何衣橱写入。"""

    recognizer = create_recognizer(
        WardrobeItemRecognition(
            name="浅蓝色亚麻衬衫",
            category="衬衫",
            colors=(
                "浅蓝色",
            ),
            confidence=0.8,
        ),
    )

    draft = await recognize_wardrobe_image(
        recognizer=recognizer,
        user_id="user-001",
        image_base64=TEST_IMAGE_BASE64,
        content_type=WardrobeImageContentType.JPEG,
        max_image_bytes=1_024,
        min_confidence=0.5,
        image_url="https://example.test/item.jpg",
        hint="夏季衬衫",
    )

    assert draft.draft_id
    assert draft.name == "浅蓝色亚麻衬衫"
    assert draft.requires_confirmation is True
    assert draft.image_url == "https://example.test/item.jpg"

    # Provider 只接收照片和用户补充说明，不接收用户 ID
    recognizer.recognize.assert_awaited_once()
    call_args = recognizer.recognize.await_args
    assert call_args is not None
    image, hint = call_args.args
    assert image.content == TEST_IMAGE_BYTES
    assert hint == "夏季衬衫"


@pytest.mark.anyio
async def test_recognition_fails_when_provider_disabled() -> None:
    """验证未启用识别时明确失败，不返回空草稿。"""

    with pytest.raises(WardrobeVisionUnavailableError):
        await recognize_wardrobe_image(
            recognizer=None,
            user_id="user-001",
            image_base64=TEST_IMAGE_BASE64,
            content_type=WardrobeImageContentType.JPEG,
            max_image_bytes=1_024,
            min_confidence=0.5,
        )


@pytest.mark.anyio
async def test_recognition_rejects_invalid_image_before_calling_provider() -> None:
    """验证无效照片在调用外部模型之前就被拦截。"""

    recognizer = create_recognizer(
        WardrobeItemRecognition(
            confidence=0.9,
        ),
    )

    with pytest.raises(WardrobeImageError):
        await recognize_wardrobe_image(
            recognizer=recognizer,
            user_id="user-001",
            image_base64=b64encode(
                b"\x89PNG\r\n\x1a\n" + b"\x00" * 12,
            ).decode("ascii"),
            content_type=WardrobeImageContentType.JPEG,
            max_image_bytes=1_024,
            min_confidence=0.5,
        )

    recognizer.recognize.assert_not_awaited()


@pytest.mark.anyio
async def test_recognition_rejects_oversized_image() -> None:
    """验证超过体积上限的照片不会发送给外部模型。"""

    recognizer = create_recognizer(
        WardrobeItemRecognition(
            confidence=0.9,
        ),
    )

    with pytest.raises(WardrobeImageError):
        await recognize_wardrobe_image(
            recognizer=recognizer,
            user_id="user-001",
            image_base64=TEST_IMAGE_BASE64,
            content_type=WardrobeImageContentType.JPEG,
            max_image_bytes=4,
            min_confidence=0.5,
        )

    recognizer.recognize.assert_not_awaited()


@pytest.mark.anyio
async def test_recognition_propagates_provider_failure() -> None:
    """验证外部识别失败不会降级成空草稿。"""

    recognizer = AsyncMock(
        spec=WardrobeImageRecognizer,
    )
    recognizer.recognize.side_effect = WardrobeVisionProviderError(
        "识别服务不可用",
    )

    with pytest.raises(WardrobeVisionProviderError):
        await recognize_wardrobe_image(
            recognizer=recognizer,
            user_id="user-001",
            image_base64=TEST_IMAGE_BASE64,
            content_type=WardrobeImageContentType.JPEG,
            max_image_bytes=1_024,
            min_confidence=0.5,
        )


@pytest.mark.anyio
async def test_recognition_logs_only_non_sensitive_fields(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """验证识别日志不包含照片内容和识别文本。"""

    recognizer = create_recognizer(
        WardrobeItemRecognition(
            name="浅蓝色亚麻衬衫",
            category="衬衫",
            confidence=0.8,
        ),
    )

    with caplog.at_level("INFO"):
        await recognize_wardrobe_image(
            recognizer=recognizer,
            user_id="user-001",
            image_base64=TEST_IMAGE_BASE64,
            content_type=WardrobeImageContentType.JPEG,
            max_image_bytes=1_024,
            min_confidence=0.5,
        )

    logged_text = caplog.text
    assert "service.wardrobe_image_recognition.completed" in logged_text
    assert "浅蓝色亚麻衬衫" not in logged_text
    assert "user-001" not in logged_text
