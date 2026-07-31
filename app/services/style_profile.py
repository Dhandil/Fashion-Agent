"""用户长期穿搭档案应用服务。"""

from collections import defaultdict
from collections.abc import Sequence
from decimal import Decimal

from app.domain.entities.outfit import Outfit
from app.domain.entities.outfit_feedback import (
    OutfitFeedback,
    OutfitFeedbackSentiment,
)
from app.domain.entities.preference_candidate import (
    PreferenceCandidate,
    PreferenceCandidateCategory,
    PreferenceDirection,
)
from app.domain.entities.style_profile import StyleProfile
from app.domain.repositories.outfit import OutfitRepository
from app.domain.repositories.outfit_feedback import (
    OutfitFeedbackRepository,
)
from app.domain.repositories.style_profile import (
    StyleProfileRepository,
)

DEFAULT_FEEDBACK_ANALYSIS_LIMIT = 100


def build_style_preference_candidates(
    feedback_items: Sequence[OutfitFeedback],
    outfits: Sequence[Outfit],
    minimum_evidence: int = 2,
) -> tuple[PreferenceCandidate, ...]:
    """根据喜欢与不喜欢的 Outfit 统计风格偏好候选。"""

    outfits_by_id = {
        outfit.outfit_id: outfit
        for outfit in outfits
    }
    evidence: dict[
        tuple[str, PreferenceDirection],
        set[str],
    ] = defaultdict(set)
    display_values: dict[str, str] = {}

    for feedback in feedback_items:
        outfit = outfits_by_id.get(
            feedback.outfit_id,
        )

        if (
            outfit is None
            or feedback.sentiment is None
        ):
            continue

        direction = (
            PreferenceDirection.PREFER
            if feedback.sentiment
            is OutfitFeedbackSentiment.LIKE
            else PreferenceDirection.AVOID
        )

        # 同一 Outfit 内重复的风格标签只能贡献一次证据
        normalized_tags = {
            style_tag.strip().casefold(): (
                style_tag.strip()
            )
            for style_tag in outfit.style_tags
            if style_tag.strip()
        }

        for normalized_value, display_value in (
            normalized_tags.items()
        ):
            display_values.setdefault(
                normalized_value,
                display_value,
            )
            evidence[
                (
                    normalized_value,
                    direction,
                )
            ].add(outfit.outfit_id)

    candidates: list[PreferenceCandidate] = []

    for normalized_value, display_value in (
        display_values.items()
    ):
        preferred_outfit_ids = evidence[
            (
                normalized_value,
                PreferenceDirection.PREFER,
            )
        ]
        avoided_outfit_ids = evidence[
            (
                normalized_value,
                PreferenceDirection.AVOID,
            )
        ]

        # 证据相同代表方向不明确，不生成可能误导用户的候选
        if len(preferred_outfit_ids) == len(
            avoided_outfit_ids,
        ):
            continue

        if len(preferred_outfit_ids) > len(
            avoided_outfit_ids,
        ):
            direction = PreferenceDirection.PREFER
            supporting_ids = preferred_outfit_ids
            opposing_ids = avoided_outfit_ids
        else:
            direction = PreferenceDirection.AVOID
            supporting_ids = avoided_outfit_ids
            opposing_ids = preferred_outfit_ids

        if len(supporting_ids) < minimum_evidence:
            continue

        candidates.append(
            PreferenceCandidate(
                category=(
                    PreferenceCandidateCategory.STYLE
                ),
                value=display_value,
                direction=direction,
                evidence_count=len(supporting_ids),
                opposing_evidence_count=len(
                    opposing_ids,
                ),
                evidence_outfit_ids=tuple(
                    sorted(supporting_ids),
                ),
            ),
        )

    return tuple(
        sorted(
            candidates,
            key=lambda candidate: (
                -candidate.evidence_count,
                candidate.value.casefold(),
                candidate.direction.value,
            ),
        ),
    )


async def analyze_style_preference_candidates(
    outfit_repository: OutfitRepository,
    feedback_repository: OutfitFeedbackRepository,
    user_id: str,
    minimum_evidence: int = 2,
    feedback_limit: int = (
        DEFAULT_FEEDBACK_ANALYSIS_LIMIT
    ),
) -> tuple[PreferenceCandidate, ...]:
    """查询当前用户反馈并动态生成可追踪的风格候选。"""

    feedback_items = await feedback_repository.search(
        user_id=user_id,
        limit=feedback_limit,
    )

    if not feedback_items:
        return ()

    outfit_ids = tuple(
        feedback.outfit_id
        for feedback in feedback_items
    )
    outfits = await outfit_repository.get_by_ids(
        user_id=user_id,
        outfit_ids=outfit_ids,
    )

    return build_style_preference_candidates(
        feedback_items=feedback_items,
        outfits=outfits,
        minimum_evidence=minimum_evidence,
    )


async def get_style_profile(
    repository: StyleProfileRepository,
    user_id: str,
) -> StyleProfile:
    """读取当前用户档案；不存在时返回未持久化的空档案。"""

    profile = await repository.get_by_user_id(
        user_id,
    )

    if profile is not None:
        return profile

    return StyleProfile(
        user_id=user_id,
    )


async def replace_style_profile(
    repository: StyleProfileRepository,
    user_id: str,
    preferred_styles: tuple[str, ...] = (),
    preferred_colors: tuple[str, ...] = (),
    avoided_colors: tuple[str, ...] = (),
    preferred_fits: tuple[str, ...] = (),
    avoided_materials: tuple[str, ...] = (),
    common_scenarios: tuple[str, ...] = (),
    typical_budget_min: Decimal | None = None,
    typical_budget_max: Decimal | None = None,
    notes: str | None = None,
) -> StyleProfile:
    """用用户明确提交的内容完整替换长期穿搭档案。"""

    profile = StyleProfile(
        user_id=user_id,
        preferred_styles=preferred_styles,
        preferred_colors=preferred_colors,
        avoided_colors=avoided_colors,
        preferred_fits=preferred_fits,
        avoided_materials=avoided_materials,
        common_scenarios=common_scenarios,
        typical_budget_min=typical_budget_min,
        typical_budget_max=typical_budget_max,
        notes=notes,
    )

    return await repository.save(
        profile,
    )
