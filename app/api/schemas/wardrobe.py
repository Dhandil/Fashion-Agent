"""用户衣橱 API 数据结构。"""

from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from app.domain.entities.wardrobe_image import (
    WardrobeImageContentType,
)
from app.domain.entities.wardrobe_item import (
    WardrobeItemStatus,
)

# Base64 编码后的照片长度上限，约等于 15 MB 原始字节
# 具体体积限制仍由配置和领域校验决定，这里只拦截明显异常的请求体
_MAX_IMAGE_BASE64_CHARS = 20_000_000


class WardrobeItemBase(BaseModel):
    """衣橱单品请求和响应共享字段。"""

    name: str = Field(
        min_length=1,
        max_length=200,
    )
    category: str = Field(
        min_length=1,
        max_length=100,
    )
    brand: str | None = Field(
        default=None,
        max_length=100,
    )
    colors: tuple[str, ...] = ()
    materials: tuple[str, ...] = ()
    size: str | None = Field(
        default=None,
        max_length=50,
    )
    style_tags: tuple[str, ...] = ()
    seasons: tuple[str, ...] = ()
    scenarios: tuple[str, ...] = ()
    image_url: str | None = Field(
        default=None,
        max_length=1000,
    )
    image_asset_id: str | None = Field(default=None, max_length=100)
    status: WardrobeItemStatus = WardrobeItemStatus.AVAILABLE
    notes: str | None = Field(
        default=None,
        max_length=1000,
    )


class WardrobeItemCreate(WardrobeItemBase):
    """创建衣橱单品的请求体。"""


class WardrobeItemPatch(BaseModel):
    """局部修改衣橱单品的请求体。"""

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )
    category: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )
    brand: str | None = Field(
        default=None,
        max_length=100,
    )
    colors: tuple[str, ...] | None = None
    materials: tuple[str, ...] | None = None
    size: str | None = Field(
        default=None,
        max_length=50,
    )
    style_tags: tuple[str, ...] | None = None
    seasons: tuple[str, ...] | None = None
    scenarios: tuple[str, ...] | None = None
    image_url: str | None = Field(
        default=None,
        max_length=1000,
    )
    status: WardrobeItemStatus | None = None
    notes: str | None = Field(
        default=None,
        max_length=1000,
    )

    @model_validator(mode="after")
    def validate_non_nullable_fields(
        self,
    ) -> "WardrobeItemPatch":
        """阻止必填标量和序列使用 null 清空。"""

        non_nullable_fields = (
            "name",
            "category",
            "colors",
            "materials",
            "style_tags",
            "seasons",
            "scenarios",
            "status",
        )

        for field_name in non_nullable_fields:
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(
                    f"{field_name} 不能为 null",
                )

        return self


class WardrobeItemStatusUpdate(BaseModel):
    """单独修改衣橱单品可用状态的请求体。"""

    status: WardrobeItemStatus


class WardrobeItemResponse(WardrobeItemBase):
    """返回给客户端的衣橱单品。"""

    wardrobe_item_id: str = Field(
        min_length=1,
        max_length=100,
    )

    # 允许从领域实体的属性读取字段
    model_config = ConfigDict(
        from_attributes=True,
    )


class WardrobeImageRecognitionRequest(BaseModel):
    """提交一张衣物照片请求识别的请求体。"""

    # 照片使用 Base64 传输，服务端不保存原始字节
    image_base64: str | None = Field(
        default=None,
        min_length=1,
        max_length=_MAX_IMAGE_BASE64_CHARS,
    )

    # 本地文件卷流程使用已经上传完成的图片资产 ID
    image_asset_id: str | None = Field(default=None, max_length=100)

    # 客户端声明的照片格式，服务端仍会按文件头再次校验
    content_type: WardrobeImageContentType | None = None

    # 客户端已经托管的照片地址，确认后可以随衣物一起保存
    image_url: str | None = Field(
        default=None,
        max_length=1000,
    )

    # 用户主动提供的补充说明，例如“这是一件羊毛大衣”
    hint: str | None = Field(
        default=None,
        max_length=200,
    )

    @model_validator(mode="after")
    def validate_image_input(self) -> "WardrobeImageRecognitionRequest":
        """Base64 和图片资产二选一，避免空请求或重复上传。"""

        if (self.image_base64 is None) == (self.image_asset_id is None):
            raise ValueError("image_base64 和 image_asset_id 必须二选一")
        if self.image_base64 is not None and self.content_type is None:
            raise ValueError("使用 image_base64 时必须提供 content_type")
        return self


class WardrobeImageUploadRequest(BaseModel):
    """创建本地文件卷上传凭证。"""

    content_type: WardrobeImageContentType
    byte_size: int = Field(ge=1, le=20 * 1024 * 1024)


class WardrobeImageUploadResponse(BaseModel):
    """返回给前端的本地上传地址和资产信息。"""

    image_asset_id: str
    upload_url: str
    content_url: str
    expires_at: datetime


class WardrobeImageAssetResponse(BaseModel):
    """上传完成后的图片资产元数据。"""

    image_asset_id: str
    content_type: WardrobeImageContentType
    byte_size: int
    sha256: str
    status: str
    content_url: str


class WardrobeItemDraftResponse(BaseModel):
    """返回给客户端的待确认衣橱单品草稿。

    草稿不是衣橱事实。用户确认或修正后，需要再调用新增衣橱单品接口
    才会写入衣橱。
    """

    draft_id: str = Field(
        min_length=1,
        max_length=100,
    )
    name: str | None = Field(
        default=None,
        max_length=200,
    )
    category: str | None = Field(
        default=None,
        max_length=100,
    )
    colors: tuple[str, ...] = ()
    materials: tuple[str, ...] = ()
    style_tags: tuple[str, ...] = ()
    seasons: tuple[str, ...] = ()
    scenarios: tuple[str, ...] = ()
    notes: str | None = Field(
        default=None,
        max_length=1000,
    )
    image_url: str | None = Field(
        default=None,
        max_length=1000,
    )
    image_asset_id: str | None = Field(default=None, max_length=100)
    confidence: float = Field(
        ge=0,
        le=1,
    )
    uncertain_fields: tuple[str, ...] = ()
    missing_fields: tuple[str, ...] = ()
    unrecognizable_fields: tuple[str, ...] = ()
    requires_confirmation: bool = True

    # 允许从领域实体的属性读取字段
    model_config = ConfigDict(
        from_attributes=True,
    )


class WardrobeItemListResponse(BaseModel):
    """当前用户衣橱分页列表响应。"""

    items: tuple[WardrobeItemResponse, ...] = ()
    count: int = Field(
        ge=0,
    )
    total: int = Field(
        ge=0,
    )
    limit: int = Field(
        ge=1,
    )
    offset: int = Field(
        ge=0,
    )
