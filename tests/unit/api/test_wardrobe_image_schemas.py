"""衣物图片识别请求结构测试。"""

import pytest
from pydantic import ValidationError

from app.api.schemas.wardrobe import WardrobeImageRecognitionRequest


def test_asset_recognition_does_not_require_content_type() -> None:
    """已上传资产只需要资产 ID，避免重复提交文件类型。"""

    request = WardrobeImageRecognitionRequest(
        image_asset_id="asset-001",
    )

    assert request.image_asset_id == "asset-001"
    assert request.content_type is None


def test_base64_recognition_requires_content_type() -> None:
    """兼容旧 Base64 流程时仍必须声明图片类型。"""

    with pytest.raises(ValidationError, match="content_type"):
        WardrobeImageRecognitionRequest(image_base64="aGVsbG8=")


def test_recognition_requires_exactly_one_image_source() -> None:
    """请求不能同时提交或同时省略 Base64 与本地资产 ID。"""

    with pytest.raises(ValidationError):
        WardrobeImageRecognitionRequest()

    with pytest.raises(ValidationError):
        WardrobeImageRecognitionRequest(
            image_base64="aGVsbG8=",
            image_asset_id="asset-001",
            content_type="image/jpeg",
        )
