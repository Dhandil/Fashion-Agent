"""用户长期穿搭档案应用服务测试。"""

from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import (
    PreferenceCandidateUnavailableError,
    StyleProfileUpdateConflictError,
)
from app.domain.entities.outfit import Outfit, OutfitItem
from app.domain.entities.outfit_feedback import (
    OutfitFeedback,
    OutfitFeedbackSentiment,
)
from app.domain.entities.preference_candidate import (
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
from app.services.style_profile import (
    analyze_style_preference_candidates,
    build_style_preference_candidates,
    confirm_style_preference_candidate,
    get_style_profile,
    patch_style_profile,
    replace_style_profile,
)


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

    profile = await confirm_style_preference_candidate(
        style_profile_repository=style_repository,
        outfit_repository=outfit_repository,
        feedback_repository=feedback_repository,
        user_id="user-001",
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

    profile = await confirm_style_preference_candidate(
        style_profile_repository=style_repository,
        outfit_repository=outfit_repository,
        feedback_repository=feedback_repository,
        user_id="user-001",
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

    with pytest.raises(
        PreferenceCandidateUnavailableError,
        match="证据不足",
    ):
        await confirm_style_preference_candidate(
            style_profile_repository=style_repository,
            outfit_repository=outfit_repository,
            feedback_repository=feedback_repository,
            user_id="user-001",
            value="休闲",
            direction=PreferenceDirection.PREFER,
        )

    style_repository.get_by_user_id.assert_not_awaited()
    style_repository.save.assert_not_awaited()
