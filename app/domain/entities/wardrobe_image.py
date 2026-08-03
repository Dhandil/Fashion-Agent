"""用户上传的衣物照片领域实体。"""

from enum import StrEnum

from pydantic import (
    BaseModel,
    ConfigDict,
)


class WardrobeImageContentType(StrEnum):
    """当前允许上传的衣物照片格式。"""

    JPEG = "image/jpeg"
    PNG = "image/png"
    WEBP = "image/webp"


class WardrobeImage(BaseModel):
    """一张等待识别的衣物照片。

    照片只在当前请求内用于识别，不写入数据库，也不进入日志和 Trace。
    """

    # 照片原始字节，由 API 层从传输编码解码后提供
    content: bytes

    # 客户端声明的照片格式，仍需与实际字节特征一致
    content_type: WardrobeImageContentType

    # 领域对象创建后不能被原地修改
    model_config = ConfigDict(
        frozen=True,
    )
