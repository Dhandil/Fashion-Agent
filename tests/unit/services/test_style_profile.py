"""用户长期穿搭档案应用服务测试。"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import (
    PreferenceCandidateUnavailableError,
    PreferenceMemoryNotFoundError,
    PreferenceMemoryUpdateConflictError,
    StyleProfileUpdateConflictError,
)
from app.domain.entities.outfit import Outfit, OutfitItem
from app.domain.entities.outfit_feedback import (
    OutfitFeedback,
    OutfitFeedbackSentiment,
)
from app.domain.entities.preference_candidate import (
    PreferenceCandidateCategory,
    PreferenceDirection,
    create_preference_candidate_id,
)
from app.domain.entities.preference_memory import (
    PreferenceMemory,
    PreferenceMemorySource,
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
from app.services.style_profile import (
    analyze_style_preference_candidates,
    build_style_preference_candidates,
    confirm_style_preference_candidate,
    delete_preference_memory,
    delete_style_profile,
    get_style_profile,
    list_preference_memories,
    patch_style_profile,
    replace_style_profile,
    set_preference_memory_expiry,
)


@pytest.mark.anyio
async def test_delete_style_profile_delegates_to_repository() -> None:
    """验证长期档案删除只作用于当前用户，并返回删除结果。"""

    repository = AsyncMock(
        spec=StyleProfileRepository,
    )
    repository.delete_by_user_id.return_value = True
    memory_repository = AsyncMock(
        spec=PreferenceMemoryRepository,
    )
    memory_repository.delete_by_user_id.return_value = 2

    deleted = await delete_style_profile(
        repository=repository,
        preference_memory_repository=memory_repository,
        user_id="user-001",
    )

    repository.delete_by_user_id.assert_awaited_once_with(
        "user-001",
    )
    memory_repository.delete_by_user_id.assert_awaited_once_with(
        "user-001",
    )
    assert deleted is True


def create_feedback_outfit(
    outfit_id: str,
    style_tags: tuple[str, ...],
) -> Outfit:
    """创建候选分析使用的结构化 Outfit。"""

    return Outfit(
        outfit_id=outfit_id,
        user_id="user-001",
        name=f"测试穿搭 {outfit_id}",
        scenario="日常",
        style_tags=style_tags,
        items=(
            OutfitItem(
                role="上装",
                name="测试上装",
                source="recommendation",
            ),
        ),
        recommendation_reason="候选偏好测试。",
    )


def create_feedback(
    outfit_id: str,
    sentiment: OutfitFeedbackSentiment,
) -> OutfitFeedback:
    """创建指向指定 Outfit 的反馈。"""

    return OutfitFeedback(
        user_id="user-001",
        outfit_id=outfit_id,
        sentiment=sentiment,
    )


def create_preference_memory(
    *,
    expires_at: datetime | None = None,
) -> PreferenceMemory:
    """创建长期偏好列表测试记录。"""

    confirmed_at = datetime(
        2026,
        8,
        2,
        10,
        tzinfo=UTC,
    )
    return PreferenceMemory(
        preference_memory_id=(
            "pm_0123456789abcdef0123456789abcdef"
        ),
        user_id="user-001",
        category=PreferenceCandidateCategory.STYLE,
        value="休闲",
        direction=PreferenceDirection.PREFER,
        source=(
            PreferenceMemorySource.OUTFIT_FEEDBACK_CONFIRMATION
        ),
        source_reference_ids=("outfit-001",),
        confirmed_at=confirmed_at,
        last_confirmed_at=confirmed_at,
        expires_at=expires_at,
    )


@pytest.mark.anyio
async def test_list_preference_memories_filters_expired_records() -> None:
    """验证默认只返回仍然有效的长期偏好审计。"""

    reference_time = datetime(
        2026,
        8,
        10,
        tzinfo=UTC,
    )
    active = create_preference_memory()
    expired = create_preference_memory(
        expires_at=reference_time - timedelta(days=1),
    ).model_copy(
        update={
            "preference_memory_id": (
                "pm_fedcba9876543210fedcba9876543210"
            ),
            "value": "复古",
        },
    )
    repository = AsyncMock(
        spec=PreferenceMemoryRepository,
    )
    repository.list_by_user_id.return_value = (
        active,
        expired,
    )

    visible = await list_preference_memories(
        repository=repository,
        user_id="user-001",
        at=reference_time,
    )
    all_records = await list_preference_memories(
        repository=repository,
        user_id="user-001",
        include_expired=True,
        at=reference_time,
    )

    assert visible == (active,)
    assert all_records == (active, expired)


@pytest.mark.anyio
async def test_set_preference_memory_expiry_saves_valid_time() -> None:
    """验证用户可以设置或清除一条偏好的过期时间。"""

    memory = create_preference_memory()
    expires_at = memory.last_confirmed_at + timedelta(days=30)
    repository = AsyncMock(
        spec=PreferenceMemoryRepository,
    )
    repository.get_by_id.return_value = memory
    repository.save.side_effect = lambda item: item

    updated = await set_preference_memory_expiry(
        repository=repository,
        user_id="user-001",
        preference_memory_id=memory.preference_memory_id,
        expires_at=expires_at,
    )

    assert updated.expires_at == expires_at
    repository.save.assert_awaited_once_with(updated)


@pytest.mark.anyio
async def test_set_preference_memory_expiry_rejects_invalid_time() -> None:
    """验证过期时间不能早于最近确认时间。"""

    memory = create_preference_memory()
    repository = AsyncMock(
        spec=PreferenceMemoryRepository,
    )
    repository.get_by_id.return_value = memory

    with pytest.raises(
        PreferenceMemoryUpdateConflictError,
        match="晚于最近确认时间",
    ):
        await set_preference_memory_expiry(
            repository=repository,
            user_id="user-001",
            preference_memory_id=(
                memory.preference_memory_id
            ),
            expires_at=memory.last_confirmed_at,
        )

    repository.save.assert_not_awaited()


@pytest.mark.anyio
async def test_set_preference_memory_expiry_rejects_missing_record() -> None:
    """验证其他用户或不存在的记录不会被修改。"""

    repository = AsyncMock(
        spec=PreferenceMemoryRepository,
    )
    repository.get_by_id.return_value = None

    with pytest.raises(PreferenceMemoryNotFoundError):
        await set_preference_memory_expiry(
            repository=repository,
            user_id="user-001",
            preference_memory_id=(
                "pm_0123456789abcdef0123456789abcdef"
            ),
            expires_at=None,
        )


@pytest.mark.anyio
async def test_delete_preference_memory_updates_profile() -> None:
    """验证删除审计记录时同步移除其同向档案偏好。"""

    memory = create_preference_memory()
    memory_repository = AsyncMock(
        spec=PreferenceMemoryRepository,
    )
    memory_repository.get_by_id.return_value = memory
    memory_repository.delete_by_id.return_value = True
    style_repository = AsyncMock(
        spec=StyleProfileRepository,
    )
    style_repository.get_by_user_id.return_value = StyleProfile(
        user_id="user-001",
        preferred_styles=("休闲", "简约"),
    )
    style_repository.save.side_effect = lambda profile: profile

    deleted = await delete_preference_memory(
        style_profile_repository=style_repository,
        preference_memory_repository=memory_repository,
        user_id="user-001",
        preference_memory_id=memory.preference_memory_id,
    )

    saved_profile = style_repository.save.await_args.args[0]
    assert saved_profile.preferred_styles == ("简约",)
    assert deleted is True
    memory_repository.delete_by_id.assert_awaited_once_with(
        user_id="user-001",
        preference_memory_id=memory.preference_memory_id,
    )


@pytest.mark.anyio
async def test_get_style_profile_returns_empty_profile() -> None:
    """验证档案不存在时返回空领域实体但不写入仓库。"""

    repository = AsyncMock(
        spec=StyleProfileRepository,
    )
    repository.get_by_user_id.return_value = None

    profile = await get_style_profile(
        repository=repository,
        user_id="user-001",
    )

    assert profile == StyleProfile(
        user_id="user-001",
    )
    repository.save.assert_not_awaited()


@pytest.mark.anyio
async def test_replace_style_profile_uses_current_user() -> None:
    """验证服务用当前用户和明确提交内容替换档案。"""

    repository = AsyncMock(
        spec=StyleProfileRepository,
    )
    repository.save.side_effect = (
        lambda profile: profile
    )

    profile = await replace_style_profile(
        repository=repository,
        user_id="user-001",
        preferred_styles=(
            "简约",
            "休闲",
        ),
        avoided_styles=(
            "街头",
        ),
        preferred_colors=(
            "浅蓝色",
        ),
        typical_budget_min=Decimal(100),
        typical_budget_max=Decimal(500),
        notes="不要过于正式",
    )

    assert profile.user_id == "user-001"
    assert profile.preferred_styles == (
        "简约",
        "休闲",
    )
    assert profile.avoided_styles == (
        "街头",
    )
    assert profile.preferred_colors == (
        "浅蓝色",
    )
    assert profile.notes == "不要过于正式"
    repository.save.assert_awaited_once_with(
        profile,
    )


@pytest.mark.anyio
async def test_patch_style_profile_preserves_omitted_fields() -> None:
    """验证部分更新只替换明确提供的字段。"""

    repository = AsyncMock(
        spec=StyleProfileRepository,
    )
    repository.get_by_user_id.return_value = (
        StyleProfile(
            user_id="user-001",
            preferred_styles=(
                "简约",
            ),
            preferred_colors=(
                "浅蓝色",
            ),
            notes="原说明",
        )
    )
    repository.save.side_effect = (
        lambda profile: profile
    )

    profile = await patch_style_profile(
        repository=repository,
        user_id="user-001",
        changes={
            "notes": "更新后的说明",
        },
    )

    assert profile.preferred_styles == (
        "简约",
    )
    assert profile.preferred_colors == (
        "浅蓝色",
    )
    assert profile.notes == "更新后的说明"
    repository.save.assert_awaited_once_with(
        profile,
    )


@pytest.mark.anyio
async def test_patch_style_profile_empty_changes_does_not_save() -> None:
    """验证空 PATCH 只返回当前档案，不产生无意义写入。"""

    repository = AsyncMock(
        spec=StyleProfileRepository,
    )
    current_profile = StyleProfile(
        user_id="user-001",
        preferred_styles=(
            "简约",
        ),
    )
    repository.get_by_user_id.return_value = (
        current_profile
    )

    profile = await patch_style_profile(
        repository=repository,
        user_id="user-001",
        changes={},
    )

    assert profile is current_profile
    repository.save.assert_not_awaited()


@pytest.mark.anyio
async def test_patch_style_profile_rejects_merged_conflict() -> None:
    """验证局部更新与已有偏好冲突时不写入仓库。"""

    repository = AsyncMock(
        spec=StyleProfileRepository,
    )
    repository.get_by_user_id.return_value = (
        StyleProfile(
            user_id="user-001",
            preferred_styles=(
                "简约",
            ),
        )
    )

    with pytest.raises(
        StyleProfileUpdateConflictError,
        match="互相冲突",
    ):
        await patch_style_profile(
            repository=repository,
            user_id="user-001",
            changes={
                "avoided_styles": (
                    "简约",
                ),
            },
        )

    repository.save.assert_not_awaited()


def test_build_style_candidates_tracks_opposing_evidence() -> None:
    """验证候选记录支持方向、反向证据和关联 Outfit。"""

    outfits = (
        create_feedback_outfit(
            "outfit-001",
            (
                "简约",
                "简约",
            ),
        ),
        create_feedback_outfit(
            "outfit-002",
            (
                "简约",
            ),
        ),
        create_feedback_outfit(
            "outfit-003",
            (
                "简约",
            ),
        ),
    )
    feedback_items = (
        create_feedback(
            "outfit-001",
            OutfitFeedbackSentiment.LIKE,
        ),
        create_feedback(
            "outfit-002",
            OutfitFeedbackSentiment.LIKE,
        ),
        create_feedback(
            "outfit-003",
            OutfitFeedbackSentiment.DISLIKE,
        ),
    )

    candidates = build_style_preference_candidates(
        feedback_items=feedback_items,
        outfits=outfits,
        minimum_evidence=2,
    )

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.value == "简约"
    assert candidate.candidate_id.startswith("pc_")
    assert candidate.source.value == "outfit_feedback"
    assert candidate.direction is PreferenceDirection.PREFER
    assert candidate.evidence_count == 2
    assert candidate.opposing_evidence_count == 1
    assert candidate.evidence_outfit_ids == (
        "outfit-001",
        "outfit-002",
    )


def test_build_style_candidates_skips_tied_evidence() -> None:
    """验证方向相同票数时不会生成误导性的候选。"""

    outfits = (
        create_feedback_outfit(
            "outfit-001",
            (
                "街头",
            ),
        ),
        create_feedback_outfit(
            "outfit-002",
            (
                "街头",
            ),
        ),
        create_feedback_outfit(
            "outfit-003",
            (
                "街头",
            ),
        ),
        create_feedback_outfit(
            "outfit-004",
            (
                "街头",
            ),
        ),
    )
    feedback_items = (
        create_feedback(
            "outfit-001",
            OutfitFeedbackSentiment.LIKE,
        ),
        create_feedback(
            "outfit-002",
            OutfitFeedbackSentiment.LIKE,
        ),
        create_feedback(
            "outfit-003",
            OutfitFeedbackSentiment.DISLIKE,
        ),
        create_feedback(
            "outfit-004",
            OutfitFeedbackSentiment.DISLIKE,
        ),
    )

    assert (
        build_style_preference_candidates(
            feedback_items=feedback_items,
            outfits=outfits,
        )
        == ()
    )


@pytest.mark.anyio
async def test_analyze_style_candidates_uses_batch_queries() -> None:
    """验证服务使用反馈查询和 Outfit 批量查询动态分析。"""

    feedback_items = [
        create_feedback(
            "outfit-001",
            OutfitFeedbackSentiment.LIKE,
        ),
        create_feedback(
            "outfit-002",
            OutfitFeedbackSentiment.LIKE,
        ),
    ]
    outfit_repository = AsyncMock(
        spec=OutfitRepository,
    )
    outfit_repository.get_by_ids.return_value = [
        create_feedback_outfit(
            "outfit-001",
            (
                "休闲",
            ),
        ),
        create_feedback_outfit(
            "outfit-002",
            (
                "休闲",
            ),
        ),
    ]
    feedback_repository = AsyncMock(
        spec=OutfitFeedbackRepository,
    )
    feedback_repository.search.return_value = (
        feedback_items
    )

    candidates = await analyze_style_preference_candidates(
        outfit_repository=outfit_repository,
        feedback_repository=feedback_repository,
        user_id="user-001",
        minimum_evidence=2,
    )

    assert candidates[0].value == "休闲"
    feedback_repository.search.assert_awaited_once_with(
        user_id="user-001",
        limit=100,
    )
    outfit_repository.get_by_ids.assert_awaited_once_with(
        user_id="user-001",
        outfit_ids=(
            "outfit-001",
            "outfit-002",
        ),
    )


@pytest.mark.anyio
async def test_confirm_preferred_style_updates_profile() -> None:
    """验证确认偏好候选时加入喜欢并移除相同避免风格。"""

    feedback_items = [
        create_feedback(
            outfit_id,
            OutfitFeedbackSentiment.LIKE,
        )
        for outfit_id in (
            "outfit-001",
            "outfit-002",
        )
    ]
    outfits = [
        create_feedback_outfit(
            outfit_id,
            (
                "休闲",
            ),
        )
        for outfit_id in (
            "outfit-001",
            "outfit-002",
        )
    ]
    outfit_repository = AsyncMock(
        spec=OutfitRepository,
    )
    outfit_repository.get_by_ids.return_value = outfits
    feedback_repository = AsyncMock(
        spec=OutfitFeedbackRepository,
    )
    feedback_repository.search.return_value = (
        feedback_items
    )
    style_repository = AsyncMock(
        spec=StyleProfileRepository,
    )
    style_repository.get_by_user_id.return_value = (
        StyleProfile(
            user_id="user-001",
            preferred_styles=(
                "简约",
            ),
            avoided_styles=(
                "休闲",
            ),
        )
    )
    style_repository.save.side_effect = (
        lambda profile: profile
    )
    memory_repository = AsyncMock(
        spec=PreferenceMemoryRepository,
    )
    existing_memory = create_preference_memory().model_copy(
        update={
            "direction": PreferenceDirection.AVOID,
        },
    )
    memory_repository.get_by_identity.return_value = (
        existing_memory
    )
    memory_repository.save.side_effect = (
        lambda memory: memory
    )

    profile = await confirm_style_preference_candidate(
        style_profile_repository=style_repository,
        outfit_repository=outfit_repository,
        feedback_repository=feedback_repository,
        preference_memory_repository=memory_repository,
        user_id="user-001",
        candidate_id=create_preference_candidate_id(
            category=PreferenceCandidateCategory.STYLE,
            value="休闲",
            direction=PreferenceDirection.PREFER,
            evidence_outfit_ids=(
                "outfit-001",
                "outfit-002",
            ),
        ),
        value=" 休闲 ",
        direction=PreferenceDirection.PREFER,
    )

    assert profile.preferred_styles == (
        "简约",
        "休闲",
    )
    assert profile.avoided_styles == ()
    style_repository.save.assert_awaited_once_with(
        profile,
    )
    saved_memory = memory_repository.save.await_args.args[0]
    # 同一偏好方向翻转时复用稳定记录，而不是保留冲突副本。
    assert saved_memory.preference_memory_id == (
        existing_memory.preference_memory_id
    )
    assert saved_memory.direction is PreferenceDirection.PREFER
    assert saved_memory.confirmed_at == (
        existing_memory.confirmed_at
    )
    assert saved_memory.value == "休闲"
    assert saved_memory.source_reference_ids == (
        "outfit-001",
        "outfit-002",
    )


@pytest.mark.anyio
async def test_confirm_avoided_style_updates_profile() -> None:
    """验证确认避免候选时移除相同喜欢风格。"""

    feedback_items = [
        create_feedback(
            outfit_id,
            OutfitFeedbackSentiment.DISLIKE,
        )
        for outfit_id in (
            "outfit-001",
            "outfit-002",
        )
    ]
    outfit_repository = AsyncMock(
        spec=OutfitRepository,
    )
    outfit_repository.get_by_ids.return_value = [
        create_feedback_outfit(
            outfit_id,
            (
                "街头",
            ),
        )
        for outfit_id in (
            "outfit-001",
            "outfit-002",
        )
    ]
    feedback_repository = AsyncMock(
        spec=OutfitFeedbackRepository,
    )
    feedback_repository.search.return_value = (
        feedback_items
    )
    style_repository = AsyncMock(
        spec=StyleProfileRepository,
    )
    style_repository.get_by_user_id.return_value = (
        StyleProfile(
            user_id="user-001",
            preferred_styles=(
                "街头",
            ),
        )
    )
    style_repository.save.side_effect = (
        lambda profile: profile
    )
    memory_repository = AsyncMock(
        spec=PreferenceMemoryRepository,
    )
    memory_repository.get_by_identity.return_value = None
    memory_repository.save.side_effect = (
        lambda memory: memory
    )

    profile = await confirm_style_preference_candidate(
        style_profile_repository=style_repository,
        outfit_repository=outfit_repository,
        feedback_repository=feedback_repository,
        preference_memory_repository=memory_repository,
        user_id="user-001",
        candidate_id=create_preference_candidate_id(
            category=PreferenceCandidateCategory.STYLE,
            value="街头",
            direction=PreferenceDirection.AVOID,
            evidence_outfit_ids=(
                "outfit-001",
                "outfit-002",
            ),
        ),
        value="街头",
        direction=PreferenceDirection.AVOID,
    )

    assert profile.preferred_styles == ()
    assert profile.avoided_styles == (
        "街头",
    )


@pytest.mark.anyio
async def test_confirm_style_candidate_rejects_stale_evidence() -> None:
    """验证证据不足的过期候选不能修改长期档案。"""

    outfit_repository = AsyncMock(
        spec=OutfitRepository,
    )
    outfit_repository.get_by_ids.return_value = [
        create_feedback_outfit(
            "outfit-001",
            (
                "休闲",
            ),
        ),
    ]
    feedback_repository = AsyncMock(
        spec=OutfitFeedbackRepository,
    )
    feedback_repository.search.return_value = [
        create_feedback(
            "outfit-001",
            OutfitFeedbackSentiment.LIKE,
        ),
    ]
    style_repository = AsyncMock(
        spec=StyleProfileRepository,
    )
    memory_repository = AsyncMock(
        spec=PreferenceMemoryRepository,
    )

    with pytest.raises(
        PreferenceCandidateUnavailableError,
        match="证据不足",
    ):
        await confirm_style_preference_candidate(
            style_profile_repository=style_repository,
            outfit_repository=outfit_repository,
            feedback_repository=feedback_repository,
            preference_memory_repository=memory_repository,
            user_id="user-001",
            candidate_id=("pc_" + "0" * 32),
            value="休闲",
            direction=PreferenceDirection.PREFER,
        )

    style_repository.get_by_user_id.assert_not_awaited()
    style_repository.save.assert_not_awaited()
    memory_repository.save.assert_not_awaited()


@pytest.mark.anyio
async def test_confirm_style_candidate_rejects_changed_evidence_set() -> None:
    """验证候选仍存在但证据集合变化时旧 candidate_id 失效。"""

    outfit_ids = (
        "outfit-001",
        "outfit-002",
        "outfit-003",
    )
    outfit_repository = AsyncMock(
        spec=OutfitRepository,
    )
    outfit_repository.get_by_ids.return_value = [
        create_feedback_outfit(
            outfit_id,
            ("休闲",),
        )
        for outfit_id in outfit_ids
    ]
    feedback_repository = AsyncMock(
        spec=OutfitFeedbackRepository,
    )
    feedback_repository.search.return_value = [
        create_feedback(
            outfit_id,
            OutfitFeedbackSentiment.LIKE,
        )
        for outfit_id in outfit_ids
    ]
    style_repository = AsyncMock(
        spec=StyleProfileRepository,
    )
    memory_repository = AsyncMock(
        spec=PreferenceMemoryRepository,
    )
    stale_candidate_id = create_preference_candidate_id(
        category=PreferenceCandidateCategory.STYLE,
        value="休闲",
        direction=PreferenceDirection.PREFER,
        evidence_outfit_ids=(
            "outfit-001",
            "outfit-002",
        ),
    )

    with pytest.raises(
        PreferenceCandidateUnavailableError,
        match="候选偏好已不存在",
    ):
        await confirm_style_preference_candidate(
            style_profile_repository=style_repository,
            outfit_repository=outfit_repository,
            feedback_repository=feedback_repository,
            preference_memory_repository=memory_repository,
            user_id="user-001",
            candidate_id=stale_candidate_id,
            value="休闲",
            direction=PreferenceDirection.PREFER,
        )

    style_repository.get_by_user_id.assert_not_awaited()
    style_repository.save.assert_not_awaited()
    memory_repository.save.assert_not_awaited()
