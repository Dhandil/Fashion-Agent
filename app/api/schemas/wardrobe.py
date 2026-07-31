"""用户衣橱 API 数据结构。"""

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from app.domain.entities.wardrobe_item import (
    WardrobeItemStatus,
)


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
            if (
                field_name in self.model_fields_set
                and getattr(self, field_name) is None
            ):
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
