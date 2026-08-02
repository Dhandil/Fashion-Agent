"""用户明确确认后的长期偏好审计记录。"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Self
from uuid import uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.domain.entities.preference_candidate import (
    PreferenceCandidateCategory,
    PreferenceDirection,
)


class PreferenceMemorySource(StrEnum):
    """长期偏好进入档案时经过确认的来源。"""

    OUTFIT_FEEDBACK_CONFIRMATION = (
        "outfit_feedback_confirmation"
    )


def create_preference_memory_id() -> str:
    """创建不包含用户正文的随机长期偏好记录 ID。"""

    return f"pm_{uuid4().hex}"


def normalize_preference_memory_value(value: str) -> str:
    """生成查询和唯一约束使用的规范偏好值。"""

    return value.strip().casefold()


class PreferenceMemory(BaseModel):
    """一条可追溯、可过期的已确认长期偏好。"""

    preference_memory_id: str = Field(
        pattern=r"^pm_[0-9a-f]{32}$",
    )
    user_id: str = Field(
        min_length=1,
        max_length=100,
    )
    category: PreferenceCandidateCategory
    value: str = Field(
        min_length=1,
        max_length=100,
    )
    direction: PreferenceDirection
    source: PreferenceMemorySource
    source_reference_ids: tuple[str, ...] = Field(
        min_length=1,
    )
    confirmed_at: datetime
    last_confirmed_at: datetime
    expires_at: datetime | None = None

    model_config = ConfigDict(
        frozen=True,
    )

    @field_validator("value")
    @classmethod
    def normalize_value(cls, value: str) -> str:
        """清理偏好值首尾空白。"""

        return value.strip()

    @field_validator(
        "confirmed_at",
        "last_confirmed_at",
        "expires_at",
    )
    @classmethod
    def require_timezone(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        """审计时间必须带时区，避免跨环境产生歧义。"""

        if value is not None and value.tzinfo is None:
            raise ValueError("长期偏好审计时间必须包含时区")
        return value

    @model_validator(mode="after")
    def validate_timeline(self) -> Self:
        """验证首次确认、最近确认和过期时间的先后关系。"""

        if self.last_confirmed_at < self.confirmed_at:
            raise ValueError("最近确认时间不能早于首次确认时间")
        if (
            self.expires_at is not None
            and self.expires_at <= self.last_confirmed_at
        ):
            raise ValueError("过期时间必须晚于最近确认时间")
        return self

    def is_active(
        self,
        at: datetime | None = None,
    ) -> bool:
        """判断记录在指定时间是否仍然有效。"""

        reference_time = at or datetime.now(UTC)
        if reference_time.tzinfo is None:
            raise ValueError("有效性判断时间必须包含时区")
        return (
            self.expires_at is None
            or self.expires_at > reference_time
        )
