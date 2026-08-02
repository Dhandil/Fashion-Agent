"""Agent 使用的隐私安全 Style Profile 快照。"""

from decimal import Decimal
from typing import Self

from pydantic import BaseModel, ConfigDict, Field

from app.domain.entities.style_profile import StyleProfile


class StyleProfileSnapshot(BaseModel):
    """不包含用户 ID 的长期穿搭偏好快照。"""

    preferred_styles: tuple[str, ...] = ()
    avoided_styles: tuple[str, ...] = ()
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

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    @classmethod
    def from_profile(
        cls,
        profile: StyleProfile,
    ) -> Self:
        """从领域实体复制允许进入 Agent State 的字段。"""

        return cls.model_validate(
            profile.model_dump(
                exclude={"user_id"},
            ),
        )
