"""用户长期穿搭档案 API 数据结构。"""

from datetime import datetime
from decimal import Decimal
from typing import Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

from app.domain.entities.preference_candidate import (
    PreferenceCandidateCategory,
    PreferenceCandidateSource,
    PreferenceDirection,
)
from app.domain.entities.preference_memory import (
    PreferenceMemorySource,
)
from app.domain.entities.style_profile import (
    STYLE_PROFILE_SEQUENCE_FIELDS,
    normalize_preference_values,
    validate_preference_exclusivity,
)


class PreferenceCandidateResponse(BaseModel):
    """一条由反馈推导的长期偏好候选。"""

    candidate_id: str
    category: PreferenceCandidateCategory
    source: PreferenceCandidateSource
    value: str
    direction: PreferenceDirection
    evidence_count: int = Field(
        ge=1,
    )
    opposing_evidence_count: int = Field(
        ge=0,
    )
    evidence_outfit_ids: tuple[str, ...]

    model_config = ConfigDict(
        from_attributes=True,
    )


class PreferenceCandidateListResponse(BaseModel):
    """当前用户的动态长期偏好候选列表。"""

    items: tuple[PreferenceCandidateResponse, ...] = ()
    count: int = Field(
        ge=0,
    )
    minimum_evidence: int = Field(
        ge=2,
    )


class PreferenceCandidateConfirmRequest(BaseModel):
    """确认一条当前仍然有效的长期偏好候选。"""

    candidate_id: str = Field(
        pattern=r"^pc_[0-9a-f]{32}$",
    )
    category: PreferenceCandidateCategory
    value: str = Field(
        min_length=1,
        max_length=100,
    )
    direction: PreferenceDirection
    minimum_evidence: int = Field(
        default=2,
        ge=2,
        le=20,
    )


class PreferenceMemoryResponse(BaseModel):
    """一条不暴露用户 ID 的长期偏好审计响应。"""

    preference_memory_id: str
    category: PreferenceCandidateCategory
    value: str
    direction: PreferenceDirection
    source: PreferenceMemorySource
    source_reference_ids: tuple[str, ...]
    confirmed_at: datetime
    last_confirmed_at: datetime
    expires_at: datetime | None = None

    model_config = ConfigDict(
        from_attributes=True,
    )


class PreferenceMemoryExpiryRequest(BaseModel):
    """设置或清除一条长期偏好的过期时间。"""

    # 字段必填；传 null 表示清除过期时间。
    expires_at: datetime | None

    @field_validator("expires_at")
    @classmethod
    def require_timezone(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        """显式时间必须包含时区，避免客户端时区歧义。"""

        if value is not None and value.tzinfo is None:
            raise ValueError("过期时间必须包含时区")
        return value


class PreferenceMemoryListResponse(BaseModel):
    """当前用户可见的长期偏好审计列表。"""

    items: tuple[PreferenceMemoryResponse, ...] = ()
    count: int = Field(ge=0)
    include_expired: bool = False


class StyleProfileUpsertRequest(BaseModel):
    """完整新增或替换当前用户的长期穿搭偏好。"""

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


class StyleProfilePatchRequest(BaseModel):
    """部分更新当前用户的长期穿搭档案。"""

    preferred_styles: tuple[str, ...] | None = None
    avoided_styles: tuple[str, ...] | None = None
    preferred_colors: tuple[str, ...] | None = None
    avoided_colors: tuple[str, ...] | None = None
    preferred_fits: tuple[str, ...] | None = None
    avoided_materials: tuple[str, ...] | None = None
    common_scenarios: tuple[str, ...] | None = None
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

    @field_validator(
        *STYLE_PROFILE_SEQUENCE_FIELDS,
        mode="before",
    )
    @classmethod
    def normalize_sequence_values(
        cls,
        values: object,
    ) -> object:
        """清理 PATCH 中明确提供的偏好序列。"""

        return normalize_preference_values(values)

    @model_validator(mode="after")
    def validate_patch(self) -> Self:
        """验证序列不能为 null，并检查请求内部的冲突。"""

        for field_name in STYLE_PROFILE_SEQUENCE_FIELDS:
            if (
                field_name in self.model_fields_set
                and getattr(self, field_name) is None
            ):
                raise ValueError(
                    f"{field_name} 不能为 null，清空请传空数组",
                )

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
            preferred_styles=self.preferred_styles
            or (),
            avoided_styles=self.avoided_styles
            or (),
            preferred_colors=self.preferred_colors
            or (),
            avoided_colors=self.avoided_colors
            or (),
        )

        return self


class StyleProfileResponse(BaseModel):
    """当前用户长期穿搭档案响应。"""

    preferred_styles: tuple[str, ...] = ()
    avoided_styles: tuple[str, ...] = ()
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

    @field_serializer(
        "typical_budget_min",
        "typical_budget_max",
        when_used="json",
    )
    def serialize_budget(
        self,
        value: Decimal | None,
    ) -> str | None:
        """将 API 中的预算金额统一序列化为两位小数。"""

        if value is None:
            return None

        return f"{value:.2f}"
