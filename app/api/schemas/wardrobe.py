"""用户衣橱 API 数据结构。"""

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
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
