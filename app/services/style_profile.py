"""用户长期穿搭档案应用服务。"""

from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal

from pydantic import ValidationError

from app.core.exceptions import (
    PreferenceCandidateUnavailableError,
    PreferenceMemoryNotFoundError,
    PreferenceMemoryUpdateConflictError,
    StyleProfileUpdateConflictError,
)
from app.domain.entities.outfit import Outfit
from app.domain.entities.outfit_feedback import (
    OutfitFeedback,
    OutfitFeedbackSentiment,
)
from app.domain.entities.preference_candidate import (
    PreferenceCandidate,
    PreferenceCandidateCategory,
    PreferenceDirection,
    create_preference_candidate_id,
)
from app.domain.entities.preference_memory import (
    PreferenceMemory,
    PreferenceMemorySource,
    create_preference_memory_id,
)
from app.domain.entities.style_profile import StyleProfile
from app.domain.repositories.outfit import OutfitRepository
from app.domain.repositories.outfit_feedback import (
    OutfitFeedbackRepository,
)
from app.domain.repositories.preference_memory import (
    PreferenceMemoryRepository,
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
                candidate_id=create_preference_candidate_id(
                    category=(
                        PreferenceCandidateCategory.STYLE
                    ),
                    value=display_value,
                    direction=direction,
                    evidence_outfit_ids=tuple(
                        sorted(supporting_ids),
                    ),
                    opposing_evidence_outfit_ids=tuple(
                        sorted(opposing_ids),
                    ),
                ),
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


def _append_unique_value(
    values: tuple[str, ...],
    new_value: str,
) -> tuple[str, ...]:
    """忽略大小写添加一个尚不存在的规范值。"""

    normalized_value = new_value.casefold()

    if any(
        value.casefold() == normalized_value
        for value in values
    ):
        return values

    return (
        *values,
        new_value,
    )


def _remove_value(
    values: tuple[str, ...],
    removed_value: str,
) -> tuple[str, ...]:
    """忽略大小写从不可变字符串元组中移除指定值。"""

    normalized_value = removed_value.casefold()

    return tuple(
        value
        for value in values
        if value.casefold() != normalized_value
    )


async def confirm_style_preference_candidate(
    style_profile_repository: StyleProfileRepository,
    outfit_repository: OutfitRepository,
    feedback_repository: OutfitFeedbackRepository,
    preference_memory_repository: (
        PreferenceMemoryRepository
    ),
    user_id: str,
    candidate_id: str,
    value: str,
    direction: PreferenceDirection,
    minimum_evidence: int = 2,
    confirmed_at: datetime | None = None,
) -> StyleProfile:
    """重新校验证据后把用户确认的风格候选合并进档案。"""

    candidates = await analyze_style_preference_candidates(
        outfit_repository=outfit_repository,
        feedback_repository=feedback_repository,
        user_id=user_id,
        minimum_evidence=minimum_evidence,
    )
    normalized_value = value.strip().casefold()
    matched_candidate = next(
        (
            candidate
            for candidate in candidates
            if (
                candidate.value.casefold()
                == normalized_value
                and candidate.candidate_id == candidate_id
                and candidate.direction is direction
                and candidate.category
                is PreferenceCandidateCategory.STYLE
            )
        ),
        None,
    )

    if matched_candidate is None:
        raise PreferenceCandidateUnavailableError(
            "候选偏好已不存在、方向已变化或证据不足",
        )

    profile = await get_style_profile(
        repository=style_profile_repository,
        user_id=user_id,
    )
    confirmed_value = matched_candidate.value

    if direction is PreferenceDirection.PREFER:
        preferred_styles = _append_unique_value(
            profile.preferred_styles,
            confirmed_value,
        )
        avoided_styles = _remove_value(
            profile.avoided_styles,
            confirmed_value,
        )
    else:
        preferred_styles = _remove_value(
            profile.preferred_styles,
            confirmed_value,
        )
        avoided_styles = _append_unique_value(
            profile.avoided_styles,
            confirmed_value,
        )

    updated_profile = profile.model_copy(
        update={
            "preferred_styles": preferred_styles,
            "avoided_styles": avoided_styles,
        },
    )

    existing_memory = (
        await preference_memory_repository.get_by_identity(
            user_id=user_id,
            category=matched_candidate.category,
            value=confirmed_value,
        )
    )
    confirmation_time = confirmed_at or datetime.now(UTC)
    if confirmation_time.tzinfo is None:
        raise ValueError("偏好确认时间必须包含时区")
    memory = PreferenceMemory(
        preference_memory_id=(
            existing_memory.preference_memory_id
            if existing_memory is not None
            else create_preference_memory_id()
        ),
        user_id=user_id,
        category=matched_candidate.category,
        value=confirmed_value,
        direction=direction,
        source=(
            PreferenceMemorySource.OUTFIT_FEEDBACK_CONFIRMATION
        ),
        source_reference_ids=(
            matched_candidate.evidence_outfit_ids
        ),
        confirmed_at=(
            existing_memory.confirmed_at
            if existing_memory is not None
            else confirmation_time
        ),
        last_confirmed_at=confirmation_time,
        # 用户再次确认一条已过期记录时将其重新激活。
        expires_at=(
            existing_memory.expires_at
            if existing_memory is not None
            and existing_memory.expires_at is not None
            and existing_memory.expires_at
            > confirmation_time
            else None
        ),
    )

    saved_profile = await style_profile_repository.save(
        updated_profile,
    )
    await preference_memory_repository.save(memory)
    return saved_profile


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


async def delete_style_profile(
    repository: StyleProfileRepository,
    preference_memory_repository: (
        PreferenceMemoryRepository
    ),
    user_id: str,
) -> bool:
    """删除当前用户长期档案及审计记录，并保持幂等。"""

    await preference_memory_repository.delete_by_user_id(
        user_id,
    )
    return await repository.delete_by_user_id(user_id)


async def list_preference_memories(
    repository: PreferenceMemoryRepository,
    user_id: str,
    *,
    include_expired: bool = False,
    at: datetime | None = None,
) -> tuple[PreferenceMemory, ...]:
    """读取用户可见的偏好审计记录，默认过滤过期项。"""

    memories = await repository.list_by_user_id(
        user_id,
    )
    if include_expired:
        return memories
    reference_time = at or datetime.now(UTC)
    return tuple(
        memory
        for memory in memories
        if memory.is_active(reference_time)
    )


async def set_preference_memory_expiry(
    repository: PreferenceMemoryRepository,
    user_id: str,
    preference_memory_id: str,
    expires_at: datetime | None,
) -> PreferenceMemory:
    """设置或清除一条长期偏好的过期时间。"""

    memory = await repository.get_by_id(
        user_id=user_id,
        preference_memory_id=preference_memory_id,
    )
    if memory is None:
        raise PreferenceMemoryNotFoundError(
            "当前用户不存在指定的长期偏好记录",
        )

    # 重新验证完整实体，确保过期时间晚于最近确认时间。
    try:
        updated_memory = PreferenceMemory.model_validate(
            {
                **memory.model_dump(),
                "expires_at": expires_at,
            },
        )
    except ValidationError as exc:
        raise PreferenceMemoryUpdateConflictError(
            "过期时间必须晚于最近确认时间",
        ) from exc
    return await repository.save(updated_memory)


async def delete_preference_memory(
    style_profile_repository: StyleProfileRepository,
    preference_memory_repository: (
        PreferenceMemoryRepository
    ),
    user_id: str,
    preference_memory_id: str,
) -> bool:
    """删除一条偏好及其对 Style Profile 产生的同向影响。"""

    memory = await preference_memory_repository.get_by_id(
        user_id=user_id,
        preference_memory_id=preference_memory_id,
    )
    if memory is None:
        return False

    profile = await get_style_profile(
        repository=style_profile_repository,
        user_id=user_id,
    )
    if memory.direction is PreferenceDirection.PREFER:
        preferred_styles = _remove_value(
            profile.preferred_styles,
            memory.value,
        )
        avoided_styles = profile.avoided_styles
    else:
        preferred_styles = profile.preferred_styles
        avoided_styles = _remove_value(
            profile.avoided_styles,
            memory.value,
        )

    updated_profile = profile.model_copy(
        update={
            "preferred_styles": preferred_styles,
            "avoided_styles": avoided_styles,
        },
    )
    if updated_profile != profile:
        await style_profile_repository.save(
            updated_profile,
        )

    return await preference_memory_repository.delete_by_id(
        user_id=user_id,
        preference_memory_id=preference_memory_id,
    )


async def replace_style_profile(
    repository: StyleProfileRepository,
    user_id: str,
    preferred_styles: tuple[str, ...] = (),
    avoided_styles: tuple[str, ...] = (),
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
        avoided_styles=avoided_styles,
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


async def patch_style_profile(
    repository: StyleProfileRepository,
    user_id: str,
    changes: dict[str, object],
) -> StyleProfile:
    """把明确提供的字段合并到当前长期档案。"""

    profile = await get_style_profile(
        repository=repository,
        user_id=user_id,
    )

    if not changes:
        return profile

    merged_data = profile.model_dump()
    merged_data.update(changes)

    try:
        updated_profile = StyleProfile.model_validate(
            merged_data,
        )
    except ValidationError as exc:
        raise StyleProfileUpdateConflictError(
            "更新后的档案包含互相冲突的偏好或预算范围",
        ) from exc

    return await repository.save(
        updated_profile,
    )
