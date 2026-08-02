"""无法形成可执行 Outfit 时的结构化缺口。"""

from enum import StrEnum
from typing import Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from app.domain.entities.outfit import WardrobeGap


class CoreOutfitRole(StrEnum):
    """完整穿搭需要覆盖的稳定核心角色。"""

    UPPER = "上装"
    LOWER = "下装"
    FOOTWEAR = "鞋履"


class OutfitGapNextAction(StrEnum):
    """缺口出现后允许提供给用户的下一步。"""

    ADD_WARDROBE_ITEMS = "add_wardrobe_items"
    ADJUST_REQUIREMENTS = "adjust_requirements"
    SEARCH_PRODUCTS = "search_products"


class OutfitGapReport(BaseModel):
    """当前真实数据不足以形成完整穿搭的报告。"""

    missing_roles: tuple[CoreOutfitRole, ...] = Field(
        min_length=1,
    )
    gaps: tuple[WardrobeGap, ...] = Field(
        min_length=1,
    )
    shopping_search_allowed: bool = False
    next_actions: tuple[OutfitGapNextAction, ...] = Field(
        min_length=1,
    )
    reason: str = Field(
        min_length=1,
        max_length=1000,
    )

    model_config = ConfigDict(
        frozen=True,
    )

    @model_validator(mode="after")
    def validate_gap_consistency(self) -> Self:
        """保证角色、建议和商品权限不存在矛盾。"""

        missing_role_values = {role.value for role in self.missing_roles}
        gap_role_values = {gap.role for gap in self.gaps}
        if missing_role_values != gap_role_values:
            raise ValueError(
                "gaps 必须与 missing_roles 完全对应",
            )
        if (
            not self.shopping_search_allowed
            and OutfitGapNextAction.SEARCH_PRODUCTS in self.next_actions
        ):
            raise ValueError(
                "没有购物授权时不能提供商品搜索动作",
            )
        return self
