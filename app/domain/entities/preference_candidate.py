"""由 Outfit 反馈动态推导的长期偏好候选。"""

import hashlib
import json
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


class PreferenceCandidateSource(StrEnum):
    """候选偏好的证据来源。"""

    OUTFIT_FEEDBACK = "outfit_feedback"


def create_preference_candidate_id(
    *,
    category: PreferenceCandidateCategory,
    value: str,
    direction: PreferenceDirection,
    evidence_outfit_ids: tuple[str, ...],
    opposing_evidence_outfit_ids: tuple[str, ...] = (),
) -> str:
    """根据候选内容和完整证据集合生成稳定、不可猜正文的 ID。"""

    payload = json.dumps(
        {
            "category": category.value,
            "direction": direction.value,
            "value": value.strip().casefold(),
            "evidence_outfit_ids": sorted(
                set(evidence_outfit_ids),
            ),
            "opposing_evidence_outfit_ids": sorted(
                set(opposing_evidence_outfit_ids),
            ),
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    digest = hashlib.sha256(
        payload.encode("utf-8"),
    ).hexdigest()
    return f"pc_{digest[:32]}"


class PreferenceCandidate(BaseModel):
    """一条具有可追踪证据的长期偏好候选。"""

    candidate_id: str = Field(
        pattern=r"^pc_[0-9a-f]{32}$",
    )
    category: PreferenceCandidateCategory
    source: PreferenceCandidateSource = (
        PreferenceCandidateSource.OUTFIT_FEEDBACK
    )
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
