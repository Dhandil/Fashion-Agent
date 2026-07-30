"""穿搭方案领域实体。"""

from enum import StrEnum
from typing import Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)


class OutfitItemSource(StrEnum):
    """穿搭单品的数据来源。"""

    # 单品来自用户已有衣橱
    WARDROBE = "wardrobe"

    # 单品来自真实商品搜索结果
    PRODUCT = "product"

    # 只描述建议单品，尚未关联具体衣物或商品
    RECOMMENDATION = "recommendation"


class OutfitItem(BaseModel):
    """一套穿搭中的一个组成单品。"""

    # 单品在搭配中的作用，例如上装、下装或鞋履
    role: str = Field(
        min_length=1,
        max_length=100,
    )

    # 展示给用户的单品名称
    name: str = Field(
        min_length=1,
        max_length=200,
    )

    # 单品来自衣橱、商品搜索或通用建议
    source: OutfitItemSource

    # 衣橱单品 ID 或外部商品 ID
    source_reference_id: str | None = Field(
        default=None,
        max_length=100,
    )

    # 该单品在当前搭配中的作用说明
    reason: str | None = Field(
        default=None,
        max_length=500,
    )

    model_config = ConfigDict(
        frozen=True,
    )

    @model_validator(mode="after")
    def validate_source_reference(self) -> Self:
        """验证真实衣物或商品必须具有来源 ID。"""

        if (
            self.source
            in {
                OutfitItemSource.WARDROBE,
                OutfitItemSource.PRODUCT,
            }
            and self.source_reference_id is None
        ):
            raise ValueError(
                "衣橱或商品单品必须提供来源 ID",
            )

        return self


class Outfit(BaseModel):
    """一套完整且可执行的穿搭方案。"""

    # 穿搭方案唯一标识
    outfit_id: str = Field(
        min_length=1,
        max_length=100,
    )

    # 穿搭方案所属用户
    user_id: str = Field(
        min_length=1,
        max_length=100,
    )

    # 便于用户识别的方案名称
    name: str = Field(
        min_length=1,
        max_length=200,
    )

    # 主要适用场景，例如通勤、约会或面试
    scenario: str = Field(
        min_length=1,
        max_length=100,
    )

    # 穿搭整体风格标签
    style_tags: tuple[str, ...] = ()

    # 适用季节或天气条件
    season: str | None = Field(
        default=None,
        max_length=100,
    )

    # 一套方案至少需要包含一个单品
    items: tuple[OutfitItem, ...] = Field(
        min_length=1,
    )

    # Agent 对整套搭配的推荐理由
    recommendation_reason: str = Field(
        min_length=1,
        max_length=2000,
    )

    # 可替换方案或其他注意事项
    notes: str | None = Field(
        default=None,
        max_length=1000,
    )

    # 用户是否收藏该搭配
    is_favorite: bool = False

    model_config = ConfigDict(
        frozen=True,
    )