"""衣物照片输入校验规则测试。"""

from base64 import b64encode

import pytest

from app.core.exceptions import WardrobeImageError
from app.domain.entities.wardrobe_image import (
    WardrobeImage,
    WardrobeImageContentType,
)
from app.domain.policies.wardrobe_image import (
    decode_wardrobe_image,
    validate_wardrobe_image,
)

# 各格式的最小合法字节，仅用于校验文件头判断
JPEG_BYTES = b"\xff\xd8\xff" + b"\x00" * 12
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 12
WEBP_BYTES = b"RIFF" + b"\x00" * 4 + b"WEBP" + b"\x00" * 4


def test_decode_accepts_base64_with_line_breaks() -> None:
    """验证解码会忽略传输过程中插入的换行。"""

    encoded = b64encode(
        JPEG_BYTES,
    ).decode("ascii")
    payload = f"{encoded[:4]}\n{encoded[4:]}"

    image = decode_wardrobe_image(
        image_base64=payload,
        content_type=WardrobeImageContentType.JPEG,
    )

    assert image.content == JPEG_BYTES
    assert image.content_type is WardrobeImageContentType.JPEG


def test_decode_rejects_invalid_base64() -> None:
    """验证非法 Base64 内容返回明确的照片错误。"""

    with pytest.raises(WardrobeImageError):
        decode_wardrobe_image(
            image_base64="这不是-Base64!!",
            content_type=WardrobeImageContentType.JPEG,
        )


def test_decode_rejects_empty_payload() -> None:
    """验证空白内容不会被当成有效照片。"""

    with pytest.raises(WardrobeImageError):
        decode_wardrobe_image(
            image_base64="   \n  ",
            content_type=WardrobeImageContentType.PNG,
        )


@pytest.mark.parametrize(
    (
        "content",
        "content_type",
    ),
    [
        (
            JPEG_BYTES,
            WardrobeImageContentType.JPEG,
        ),
        (
            PNG_BYTES,
            WardrobeImageContentType.PNG,
        ),
        (
            WEBP_BYTES,
            WardrobeImageContentType.WEBP,
        ),
    ],
)
def test_validate_accepts_supported_formats(
    content: bytes,
    content_type: WardrobeImageContentType,
) -> None:
    """验证三种允许格式的文件头都能通过校验。"""

    validate_wardrobe_image(
        image=WardrobeImage(
            content=content,
            content_type=content_type,
        ),
        max_bytes=1_024,
    )


def test_validate_rejects_content_type_mismatch() -> None:
    """验证声明格式与实际字节不一致时拒绝识别。"""

    with pytest.raises(WardrobeImageError):
        validate_wardrobe_image(
            image=WardrobeImage(
                content=PNG_BYTES,
                content_type=(WardrobeImageContentType.JPEG),
            ),
            max_bytes=1_024,
        )


def test_validate_rejects_oversized_image() -> None:
    """验证超过体积上限的照片不会被发送给外部模型。"""

    with pytest.raises(WardrobeImageError) as error:
        validate_wardrobe_image(
            image=WardrobeImage(
                content=JPEG_BYTES + b"\x00" * 100,
                content_type=(WardrobeImageContentType.JPEG),
            ),
            max_bytes=32,
        )

    # 错误信息只包含限制值，不回显照片内容
    assert "32" in str(error.value)


def test_validate_rejects_truncated_content() -> None:
    """验证长度不足以判断格式的内容直接失败。"""

    with pytest.raises(WardrobeImageError):
        validate_wardrobe_image(
            image=WardrobeImage(
                content=b"\xff\xd8\xff",
                content_type=(WardrobeImageContentType.JPEG),
            ),
            max_bytes=1_024,
        )
