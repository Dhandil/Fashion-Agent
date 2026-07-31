"""由 Outfit 反馈动态推导的长期偏好候选。"""

from enum import StrEnum

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class PreferenceCandidateCategory(StrEnum):
    """候选偏好的数据类别。"""

    STYLE = "style"


class PreferenceDirection(StrEnum):
    """候选偏好的建议沉淀方向。"""

    PREFER = "prefer"
    AVOID = "avoid"


class PreferenceCandidate(BaseModel):
    """一条具有可追踪证据的长期偏好候选。"""

    category: PreferenceCandidateCategory
    value: str = Field(
        min_length=1,
        max_length=100,
    )
    direction: PreferenceDirection
    evidence_count: int = Field(
        ge=1,
    )
    opposing_evidence_count: int = Field(
        ge=0,
    )
    evidence_outfit_ids: tuple[str, ...] = Field(
        min_length=1,
    )

    model_config = ConfigDict(
        frozen=True,
    )
