"""用户穿搭档案领域实体。"""

from decimal import Decimal
from typing import Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)


class StyleProfile(BaseModel):
    """用户长期穿搭偏好和约束。"""

    # 用户唯一标识，用于关联衣橱和搭配方案
    user_id: str = Field(
        min_length=1,
        max_length=100,
    )

    # 用户喜欢的风格，例如简约、复古或街头
    preferred_styles: tuple[str, ...] = ()

    # 用户喜欢的颜色
    preferred_colors: tuple[str, ...] = ()

    # 用户希望避免的颜色
    avoided_colors: tuple[str, ...] = ()

    # 用户喜欢的版型，例如宽松、修身或直筒
    preferred_fits: tuple[str, ...] = ()

    # 用户希望避免的材质或可能不适合的材质
    avoided_materials: tuple[str, ...] = ()

    # 用户常见的穿搭场景，例如通勤、约会或运动
    common_scenarios: tuple[str, ...] = ()

    # 用户常用预算范围的最低金额
    typical_budget_min: Decimal | None = Field(
        default=None,
        ge=0,
    )

    # 用户常用预算范围的最高金额
    typical_budget_max: Decimal | None = Field(
        default=None,
        ge=0,
    )

    # 用户主动提供的其他穿搭说明
    notes: str | None = Field(
        default=None,
        max_length=1000,
    )

    # 领域实体创建后保持不可变
    model_config = ConfigDict(
        frozen=True,
    )

    @model_validator(mode="after")
    def validate_budget_range(self) -> Self:
        """验证最低预算不能高于最高预算。"""

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