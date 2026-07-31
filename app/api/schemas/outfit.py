"""穿搭保存 API 数据结构。"""

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from app.domain.entities.outfit import OutfitItem


class OutfitConfirmRequest(BaseModel):
    """确认保存当前会话中最后一套结构化推荐。"""

    conversation_id: str = Field(
        min_length=1,
        max_length=100,
        description="产生待保存穿搭推荐的会话 ID",
    )


class OutfitFavoriteUpdate(BaseModel):
    """修改一套已保存穿搭的收藏状态。"""

    is_favorite: bool = Field(
        description="是否收藏该穿搭",
    )


class OutfitResponse(BaseModel):
    """已持久化穿搭的 API 响应。"""

    outfit_id: str
    name: str
    scenario: str
    style_tags: tuple[str, ...] = ()
    season: str | None = None
    items: tuple[OutfitItem, ...]
    recommendation_reason: str
    notes: str | None = None
    is_favorite: bool = False

    # 允许直接从不可变 Outfit 领域实体读取字段
    model_config = ConfigDict(
        from_attributes=True,
    )


class OutfitListResponse(BaseModel):
    """已保存穿搭列表响应。"""

    items: tuple[OutfitResponse, ...] = ()

    # 当前响应实际返回的数量，不代表未实现分页前的总记录数
    count: int = Field(
        ge=0,
    )
