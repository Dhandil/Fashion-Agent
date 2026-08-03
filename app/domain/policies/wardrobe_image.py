"""衣物照片输入的确定性校验规则。"""

from base64 import b64decode
from binascii import Error as BinasciiError

from app.core.exceptions import WardrobeImageError
from app.domain.entities.wardrobe_image import (
    WardrobeImage,
    WardrobeImageContentType,
)

# 每种格式的文件头特征，用于确认实际字节与声明格式一致
_JPEG_SIGNATURE = b"\xff\xd8\xff"
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_WEBP_RIFF_SIGNATURE = b"RIFF"
_WEBP_FORMAT_SIGNATURE = b"WEBP"

# 判断格式所需的最小字节数，低于该长度的内容不可能是有效照片
_MIN_IMAGE_BYTES = 12


def decode_wardrobe_image(
    *,
    image_base64: str,
    content_type: WardrobeImageContentType,
) -> WardrobeImage:
    """把客户端提交的 Base64 照片解码为领域实体。"""

    # 去掉换行等传输过程中常见的空白字符，再严格校验编码
    normalized_payload = "".join(
        image_base64.split(),
    )
    if not normalized_payload:
        raise WardrobeImageError(
            "衣物照片内容不能为空。",
        )

    try:
        content = b64decode(
            normalized_payload,
            validate=True,
        )
    except (
        BinasciiError,
        ValueError,
    ) as exc:
        raise WardrobeImageError(
            "衣物照片不是有效的 Base64 内容。",
        ) from exc

    return WardrobeImage(
        content=content,
        content_type=content_type,
    )


def validate_wardrobe_image(
    *,
    image: WardrobeImage,
    max_bytes: int,
) -> None:
    """校验照片体积和实际格式，避免把无效内容发给外部模型。"""

    content = image.content

    if len(content) < _MIN_IMAGE_BYTES:
        raise WardrobeImageError(
            "衣物照片内容为空或已损坏。",
        )

    if len(content) > max_bytes:
        # 只返回限制值，不回显照片内容
        raise WardrobeImageError(
            f"衣物照片超过 {max_bytes} 字节上限，请压缩后重试。",
        )

    if not _matches_content_type(
        content=content,
        content_type=image.content_type,
    ):
        raise WardrobeImageError(
            f"衣物照片实际格式与声明的 {image.content_type.value} 不一致。",
        )


def _matches_content_type(
    *,
    content: bytes,
    content_type: WardrobeImageContentType,
) -> bool:
    """按文件头判断字节内容是否属于声明的图片格式。"""

    if content_type is WardrobeImageContentType.JPEG:
        return content.startswith(
            _JPEG_SIGNATURE,
        )

    if content_type is WardrobeImageContentType.PNG:
        return content.startswith(
            _PNG_SIGNATURE,
        )

    # WebP 的容器头为 RIFF，格式标识出现在第 9 到第 12 字节
    return content.startswith(
        _WEBP_RIFF_SIGNATURE,
    ) and content[8:12] == _WEBP_FORMAT_SIGNATURE
