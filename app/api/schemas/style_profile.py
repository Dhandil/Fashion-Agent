"""用户长期穿搭档案 API 数据结构。"""

from decimal import Decimal
from typing import Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)


class StyleProfileUpsertRequest(BaseModel):
    """完整新增或替换当前用户的长期穿搭偏好。"""

    preferred_styles: tuple[str, ...] = ()
    preferred_colors: tuple[str, ...] = ()
    avoided_colors: tuple[str, ...] = ()
    preferred_fits: tuple[str, ...] = ()
    avoided_materials: tuple[str, ...] = ()
    common_scenarios: tuple[str, ...] = ()
    typical_budget_min: Decimal | None = Field(
        default=None,
        ge=0,
    )
    typical_budget_max: Decimal | None = Field(
        default=None,
        ge=0,
    )
    notes: str | None = Field(
        default=None,
        max_length=1000,
    )

    @model_validator(mode="after")
    def validate_budget_range(self) -> Self:
        """验证常用预算最低金额不能高于最高金额。"""

        if (
            self.typical_budget_min is not None
            and self.typical_budget_max is not None
            and self.typical_budget_min
            > self.typical_budget_max
        ):
            raise ValueError(
                "最低预算不能高于最高预算",
            )

        return self


class StyleProfileResponse(BaseModel):
    """当前用户长期穿搭档案响应。"""

    preferred_styles: tuple[str, ...] = ()
    preferred_colors: tuple[str, ...] = ()
    avoided_colors: tuple[str, ...] = ()
    preferred_fits: tuple[str, ...] = ()
    avoided_materials: tuple[str, ...] = ()
    common_scenarios: tuple[str, ...] = ()
    typical_budget_min: Decimal | None = None
    typical_budget_max: Decimal | None = None
    notes: str | None = None

    # 允许从不可变 StyleProfile 领域实体读取响应字段
    model_config = ConfigDict(
        from_attributes=True,
    )
