"""用户穿搭档案领域实体。"""

from decimal import Decimal
from typing import Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

STYLE_PROFILE_SEQUENCE_FIELDS = (
    "preferred_styles",
    "avoided_styles",
    "preferred_colors",
    "avoided_colors",
    "preferred_fits",
    "avoided_materials",
    "common_scenarios",
)


def normalize_preference_values(
    values: object,
) -> object:
    """清理偏好列表中的空白、空值和大小写重复项。"""

    if not isinstance(
        values,
        (
            list,
            tuple,
            set,
        ),
    ):
        return values

    normalized_values: list[str] = []
    normalized_keys: set[str] = set()

    for value in values:
        # 非字符串交给 Pydantic 的字段类型校验生成标准错误
        if not isinstance(value, str):
            return values

        normalized_value = value.strip()

        if not normalized_value:
            continue

        normalized_key = normalized_value.casefold()

        if normalized_key in normalized_keys:
            continue

        normalized_keys.add(normalized_key)
        normalized_values.append(normalized_value)

    return tuple(normalized_values)


def validate_preference_exclusivity(
    preferred_styles: tuple[str, ...],
    avoided_styles: tuple[str, ...],
    preferred_colors: tuple[str, ...],
    avoided_colors: tuple[str, ...],
) -> None:
    """验证同一风格或颜色不能同时出现在喜欢与避免列表。"""

    preferred_style_keys = {
        value.casefold()
        for value in preferred_styles
    }
    avoided_style_keys = {
        value.casefold()
        for value in avoided_styles
    }
    preferred_color_keys = {
        value.casefold()
        for value in preferred_colors
    }
    avoided_color_keys = {
        value.casefold()
        for value in avoided_colors
    }

    if preferred_style_keys & avoided_style_keys:
        raise ValueError(
            "同一风格不能同时标记为喜欢和避免",
        )

    if preferred_color_keys & avoided_color_keys:
        raise ValueError(
            "同一颜色不能同时标记为喜欢和避免",
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

    # 用户明确希望避免的风格
    avoided_styles: tuple[str, ...] = ()

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

    @field_validator(
        *STYLE_PROFILE_SEQUENCE_FIELDS,
        mode="before",
    )
    @classmethod
    def normalize_sequence_values(
        cls,
        values: object,
    ) -> object:
        """统一清理全部偏好序列字段。"""

        return normalize_preference_values(values)

    @model_validator(mode="after")
    def validate_budget_range(self) -> Self:
        """验证预算范围以及喜欢和避免列表的互斥性。"""

        if (
            self.typical_budget_min is not None
            and self.typical_budget_max is not None
            and self.typical_budget_min
            > self.typical_budget_max
        ):
            raise ValueError(
                "最低预算不能高于最高预算",
            )

        validate_preference_exclusivity(
            preferred_styles=self.preferred_styles,
            avoided_styles=self.avoided_styles,
            preferred_colors=self.preferred_colors,
            avoided_colors=self.avoided_colors,
        )

        return self
