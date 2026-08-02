"""Outfit 可执行性检查结果。"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class OutfitIssueSeverity(StrEnum):
    """可执行性问题的严重程度。"""

    ERROR = "error"
    WARNING = "warning"


class OutfitIssueCode(StrEnum):
    """稳定的问题代码，供 API、测试和后续修正节点使用。"""

    UNKNOWN_SOURCE_ID = "unknown_source_id"
    UNAVAILABLE_WARDROBE_ITEM = "unavailable_wardrobe_item"
    OUT_OF_STOCK_PRODUCT = "out_of_stock_product"
    DUPLICATE_SOURCE_ITEM = "duplicate_source_item"
    MISSING_CORE_ROLE = "missing_core_role"
    SCENARIO_MISMATCH = "scenario_mismatch"
    HOT_WEATHER_CONFLICT = "hot_weather_conflict"
    COLD_WEATHER_RISK = "cold_weather_risk"
    PRECIPITATION_RISK = "precipitation_risk"
    AVOIDED_STYLE = "avoided_style"
    AVOIDED_COLOR = "avoided_color"
    AVOIDED_MATERIAL = "avoided_material"


class OutfitFeasibilityIssue(BaseModel):
    """一条可定位且不包含隐私正文的检查结果。"""

    code: OutfitIssueCode
    severity: OutfitIssueSeverity
    message: str = Field(
        min_length=1,
        max_length=500,
    )
    item_reference_id: str | None = Field(
        default=None,
        max_length=100,
    )

    model_config = ConfigDict(frozen=True)


class OutfitFeasibilityReport(BaseModel):
    """一套推荐能否作为最终可执行 Outfit 返回。"""

    is_executable: bool
    issues: tuple[OutfitFeasibilityIssue, ...] = ()

    model_config = ConfigDict(frozen=True)
