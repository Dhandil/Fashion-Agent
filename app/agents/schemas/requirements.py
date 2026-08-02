"""穿搭请求的结构化需求分析模型。"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RequestIntent(StrEnum):
    """当前用户请求的主要意图。"""

    KNOWLEDGE = "knowledge"
    OUTFIT = "outfit"
    OUTFIT_ADJUSTMENT = "outfit_adjustment"
    WARDROBE = "wardrobe"
    SHOPPING = "shopping"
    OTHER = "other"


class ShoppingIntent(StrEnum):
    """用户是否明确要求进入商品查询。"""

    NONE = "none"
    EXPLICIT = "explicit"


class RequirementField(StrEnum):
    """可以向用户追问的最小必要字段。"""

    SCENARIO = "scenario"
    TARGET_DATE = "target_date"
    LOCATION = "location"
    FORMALITY = "formality"
    STYLE = "style"
    ITEM_CATEGORY = "item_category"
    BUDGET = "budget"
    WEATHER = "weather"


class OutfitRequirementAnalysis(BaseModel):
    """单轮请求中可用于确定性路由的需求事实。"""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    intent: RequestIntent
    scenario: str | None = Field(
        default=None,
        max_length=100,
    )
    target_date: str | None = Field(
        default=None,
        max_length=100,
    )
    location: str | None = Field(
        default=None,
        max_length=100,
    )
    formality: str | None = Field(
        default=None,
        max_length=100,
    )
    style_preferences: tuple[str, ...] = ()
    color_preferences: tuple[str, ...] = ()
    # 只表示当前轮明确避免的内容，不自动写入长期 Style Profile
    avoided_styles: tuple[str, ...] = ()
    avoided_colors: tuple[str, ...] = ()
    avoided_materials: tuple[str, ...] = ()
    wardrobe_preferred: bool = False
    needs_wardrobe: bool = False
    needs_weather: bool = False
    shopping_intent: ShoppingIntent = ShoppingIntent.NONE
    is_sufficient: bool = True
    missing_fields: tuple[RequirementField, ...] = Field(
        default=(),
        max_length=3,
    )

    @model_validator(mode="after")
    def validate_sufficiency(self) -> "OutfitRequirementAnalysis":
        """保证充分度标记与缺失字段保持一致。"""

        if self.is_sufficient and self.missing_fields:
            raise ValueError(
                "需求充分时 missing_fields 必须为空",
            )
        if not self.is_sufficient and not self.missing_fields:
            raise ValueError(
                "需求不足时必须说明 missing_fields",
            )
        return self
