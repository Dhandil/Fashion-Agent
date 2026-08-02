"""用户长期穿搭档案 API 测试。"""

from datetime import UTC, datetime, timedelta
from unittest.mock import (
    AsyncMock,
    Mock,
)

from fastapi.testclient import TestClient

from app.api.dependencies.database import (
    get_fashion_repositories,
)
from app.core.config import (
    Settings,
    get_settings,
)
from app.db.repositories.fashion_provider import (
    FashionRepositories,
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
from app.main import create_app


def override_settings() -> Settings:
    """确保测试不读取本地开发环境配置。"""

    return Settings(
        _env_file=None,
        app_env="test",
        debug=False,
    )


def create_repositories(
    repository: StyleProfileRepository,
) -> FashionRepositories:
    """组合 Style Profile API 所需的假仓库。"""

    return FashionRepositories(
        style_profiles=repository,
        preference_memories=AsyncMock(
            spec=PreferenceMemoryRepository,
        ),
        wardrobe=Mock(),
        outfits=Mock(),
        outfit_feedback=Mock(),
    )


def create_preference_memory() -> PreferenceMemory:
    """创建长期偏好 API 测试记录。"""

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
    )


def test_delete_style_profile_is_idempotent() -> None:
    """验证删除长期档案返回 204，且不存在时不泄露状态差异。"""

    repository = AsyncMock(
        spec=StyleProfileRepository,
    )
    repository.delete_by_user_id.return_value = False
    repositories = create_repositories(repository)

    async def override_repositories() -> FashionRepositories:
        """提供当前用户没有持久化档案的假仓库。"""

        return repositories

    application = create_app()
    application.dependency_overrides[get_settings] = (
        override_settings
    )
    application.dependency_overrides[get_fashion_repositories] = (
        override_repositories
    )
    client = TestClient(application)

    try:
        response = client.delete(
            "/api/v1/style-profile",
            headers={"X-User-ID": "user-001"},
        )
    finally:
        application.dependency_overrides.clear()

    assert response.status_code == 204
    assert response.content == b""
    repository.delete_by_user_id.assert_awaited_once_with(
        "user-001",
    )


def test_get_preference_memories_returns_audit_without_user_id() -> None:
    """验证用户能查看来源和确认时间，但响应不暴露内部用户 ID。"""

    style_repository = AsyncMock(
        spec=StyleProfileRepository,
    )
    memory_repository = AsyncMock(
        spec=PreferenceMemoryRepository,
    )
    confirmed_at = datetime(
        2026,
        8,
        2,
        10,
        tzinfo=UTC,
    )
    memory_repository.list_by_user_id.return_value = (
        PreferenceMemory(
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
            source_reference_ids=(
                "outfit-001",
                "outfit-002",
            ),
            confirmed_at=confirmed_at,
            last_confirmed_at=confirmed_at,
        ),
    )
    repositories = FashionRepositories(
        style_profiles=style_repository,
        preference_memories=memory_repository,
        wardrobe=Mock(),
        outfits=Mock(),
        outfit_feedback=Mock(),
    )

    async def override_repositories() -> FashionRepositories:
        """提供固定的长期偏好审计记录。"""

        return repositories

    application = create_app()
    application.dependency_overrides[
        get_settings
    ] = override_settings
    application.dependency_overrides[
        get_fashion_repositories
    ] = override_repositories
    client = TestClient(application)

    try:
        response = client.get(
            "/api/v1/style-profile/memories",
            headers={"X-User-ID": "user-001"},
        )
    finally:
        application.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["include_expired"] is False
    assert body["items"][0]["source"] == (
        "outfit_feedback_confirmation"
    )
    assert body["items"][0]["source_reference_ids"] == [
        "outfit-001",
        "outfit-002",
    ]
    assert "user_id" not in body["items"][0]


def test_patch_preference_memory_expiry() -> None:
    """验证用户可以设置长期偏好的过期时间。"""

    memory = create_preference_memory()
    expires_at = memory.last_confirmed_at + timedelta(days=30)
    style_repository = AsyncMock(
        spec=StyleProfileRepository,
    )
    memory_repository = AsyncMock(
        spec=PreferenceMemoryRepository,
    )
    memory_repository.get_by_id.return_value = memory
    memory_repository.save.side_effect = lambda item: item
    repositories = FashionRepositories(
        style_profiles=style_repository,
        preference_memories=memory_repository,
        wardrobe=Mock(),
        outfits=Mock(),
        outfit_feedback=Mock(),
    )

    async def override_repositories() -> FashionRepositories:
        """提供固定的长期偏好记录。"""

        return repositories

    application = create_app()
    application.dependency_overrides[get_settings] = (
        override_settings
    )
    application.dependency_overrides[get_fashion_repositories] = (
        override_repositories
    )
    client = TestClient(application)

    try:
        response = client.patch(
            "/api/v1/style-profile/memories/"
            f"{memory.preference_memory_id}",
            headers={"X-User-ID": "user-001"},
            json={"expires_at": expires_at.isoformat()},
        )
    finally:
        application.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["expires_at"] == (
        expires_at.isoformat().replace("+00:00", "Z")
    )


def test_patch_missing_preference_memory_returns_404() -> None:
    """验证不存在或不属于当前用户的记录返回结构化 404。"""

    style_repository = AsyncMock(
        spec=StyleProfileRepository,
    )
    memory_repository = AsyncMock(
        spec=PreferenceMemoryRepository,
    )
    memory_repository.get_by_id.return_value = None
    repositories = FashionRepositories(
        style_profiles=style_repository,
        preference_memories=memory_repository,
        wardrobe=Mock(),
        outfits=Mock(),
        outfit_feedback=Mock(),
    )

    async def override_repositories() -> FashionRepositories:
        """提供不存在偏好记录的假仓库。"""

        return repositories

    application = create_app()
    application.dependency_overrides[get_settings] = (
        override_settings
    )
    application.dependency_overrides[get_fashion_repositories] = (
        override_repositories
    )
    client = TestClient(application)

    try:
        response = client.patch(
            "/api/v1/style-profile/memories/"
            "pm_0123456789abcdef0123456789abcdef",
            headers={"X-User-ID": "user-001"},
            json={"expires_at": None},
        )
    finally:
        application.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["code"] == (
        "preference_memory_not_found"
    )


def test_delete_preference_memory_is_idempotent() -> None:
    """验证单条删除同步档案且不会暴露记录是否存在。"""

    memory = create_preference_memory()
    style_repository = AsyncMock(
        spec=StyleProfileRepository,
    )
    style_repository.get_by_user_id.return_value = StyleProfile(
        user_id="user-001",
        preferred_styles=("休闲",),
    )
    style_repository.save.side_effect = lambda profile: profile
    memory_repository = AsyncMock(
        spec=PreferenceMemoryRepository,
    )
    memory_repository.get_by_id.return_value = memory
    memory_repository.delete_by_id.return_value = True
    repositories = FashionRepositories(
        style_profiles=style_repository,
        preference_memories=memory_repository,
        wardrobe=Mock(),
        outfits=Mock(),
        outfit_feedback=Mock(),
    )

    async def override_repositories() -> FashionRepositories:
        """提供可删除的长期偏好记录。"""

        return repositories

    application = create_app()
    application.dependency_overrides[get_settings] = (
        override_settings
    )
    application.dependency_overrides[get_fashion_repositories] = (
        override_repositories
    )
    client = TestClient(application)

    try:
        response = client.delete(
            "/api/v1/style-profile/memories/"
            f"{memory.preference_memory_id}",
            headers={"X-User-ID": "user-001"},
        )
    finally:
        application.dependency_overrides.clear()

    assert response.status_code == 204
    saved_profile = style_repository.save.await_args.args[0]
    assert saved_profile.preferred_styles == ()


def test_get_style_profile_returns_empty_profile() -> None:
    """验证没有档案时返回空结构且不产生写入。"""

    repository = AsyncMock(
        spec=StyleProfileRepository,
    )
    repository.get_by_user_id.return_value = None
    repositories = create_repositories(repository)

    async def override_repositories() -> FashionRepositories:
        """提供没有持久化档案的假仓库。"""

        return repositories

    application = create_app()
    application.dependency_overrides[
        get_settings
    ] = override_settings
    application.dependency_overrides[
        get_fashion_repositories
    ] = override_repositories
    client = TestClient(application)

    try:
        response = client.get(
            "/api/v1/style-profile",
            headers={
                "X-User-ID": "user-001",
            },
        )
    finally:
        application.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "preferred_styles": [],
        "avoided_styles": [],
        "preferred_colors": [],
        "avoided_colors": [],
        "preferred_fits": [],
        "avoided_materials": [],
        "common_scenarios": [],
        "typical_budget_min": None,
        "typical_budget_max": None,
        "notes": None,
    }
    assert "user_id" not in response.json()
    repository.save.assert_not_awaited()


def test_put_style_profile_uses_current_user() -> None:
    """验证替换档案时用户身份只能来自请求头。"""

    repository = AsyncMock(
        spec=StyleProfileRepository,
    )
    repository.save.side_effect = (
        lambda profile: profile
    )
    repositories = create_repositories(repository)

    async def override_repositories() -> FashionRepositories:
        """提供可以保存档案的假仓库。"""

        return repositories

    application = create_app()
    application.dependency_overrides[
        get_settings
    ] = override_settings
    application.dependency_overrides[
        get_fashion_repositories
    ] = override_repositories
    client = TestClient(application)

    try:
        response = client.put(
            "/api/v1/style-profile",
            headers={
                "X-User-ID": "user-001",
            },
            json={
                "preferred_styles": [
                    "简约",
                    "休闲",
                ],
                "avoided_styles": [
                    "街头",
                ],
                "preferred_colors": [
                    "浅蓝色",
                ],
                "typical_budget_min": "100",
                "typical_budget_max": "500",
                "notes": "不要过于正式",
            },
        )
    finally:
        application.dependency_overrides.clear()

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["preferred_styles"] == [
        "简约",
        "休闲",
    ]
    assert response_data["avoided_styles"] == [
        "街头",
    ]
    assert response_data["preferred_colors"] == [
        "浅蓝色",
    ]
    assert response_data["typical_budget_min"] == (
        "100.00"
    )
    assert response_data["typical_budget_max"] == (
        "500.00"
    )
    assert response_data["notes"] == "不要过于正式"
    assert "user_id" not in response_data

    saved_profile = repository.save.await_args.args[0]
    assert saved_profile.user_id == "user-001"


def test_put_style_profile_rejects_invalid_budget() -> None:
    """验证最低预算高于最高预算时请求返回 422。"""

    repository = AsyncMock(
        spec=StyleProfileRepository,
    )
    repositories = create_repositories(repository)

    async def override_repositories() -> FashionRepositories:
        """提供不应该收到无效档案的假仓库。"""

        return repositories

    application = create_app()
    application.dependency_overrides[
        get_settings
    ] = override_settings
    application.dependency_overrides[
        get_fashion_repositories
    ] = override_repositories
    client = TestClient(application)

    try:
        response = client.put(
            "/api/v1/style-profile",
            headers={
                "X-User-ID": "user-001",
            },
            json={
                "typical_budget_min": "500",
                "typical_budget_max": "100",
            },
        )
    finally:
        application.dependency_overrides.clear()

    assert response.status_code == 422
    repository.save.assert_not_awaited()


def test_put_style_profile_rejects_conflicting_preferences() -> None:
    """验证完整替换请求不能同时喜欢和避免同一风格。"""

    repository = AsyncMock(
        spec=StyleProfileRepository,
    )
    repositories = create_repositories(repository)

    async def override_repositories() -> FashionRepositories:
        """提供不应该收到冲突档案的假仓库。"""

        return repositories

    application = create_app()
    application.dependency_overrides[
        get_settings
    ] = override_settings
    application.dependency_overrides[
        get_fashion_repositories
    ] = override_repositories
    client = TestClient(application)

    try:
        response = client.put(
            "/api/v1/style-profile",
            headers={
                "X-User-ID": "user-001",
            },
            json={
                "preferred_styles": [
                    " 简约 ",
                ],
                "avoided_styles": [
                    "简约",
                ],
            },
        )
    finally:
        application.dependency_overrides.clear()

    assert response.status_code == 422
    repository.save.assert_not_awaited()


def test_patch_style_profile_preserves_omitted_fields() -> None:
    """验证 PATCH 更新说明时保留已有偏好字段。"""

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
    repositories = create_repositories(repository)

    async def override_repositories() -> FashionRepositories:
        """提供部分更新使用的假仓库。"""

        return repositories

    application = create_app()
    application.dependency_overrides[
        get_settings
    ] = override_settings
    application.dependency_overrides[
        get_fashion_repositories
    ] = override_repositories
    client = TestClient(application)

    try:
        response = client.patch(
            "/api/v1/style-profile",
            headers={
                "X-User-ID": "user-001",
            },
            json={
                "notes": "更新后的说明",
            },
        )
    finally:
        application.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["preferred_styles"] == [
        "简约",
    ]
    assert response.json()["preferred_colors"] == [
        "浅蓝色",
    ]
    assert response.json()["notes"] == "更新后的说明"


def test_patch_style_profile_empty_request_does_not_save() -> None:
    """验证空 PATCH 返回当前档案且不写入数据库。"""

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
    repositories = create_repositories(repository)

    async def override_repositories() -> FashionRepositories:
        """提供空 PATCH 使用的假仓库。"""

        return repositories

    application = create_app()
    application.dependency_overrides[
        get_settings
    ] = override_settings
    application.dependency_overrides[
        get_fashion_repositories
    ] = override_repositories
    client = TestClient(application)

    try:
        response = client.patch(
            "/api/v1/style-profile",
            headers={
                "X-User-ID": "user-001",
            },
            json={},
        )
    finally:
        application.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["preferred_styles"] == [
        "简约",
    ]
    repository.save.assert_not_awaited()


def test_patch_style_profile_rejects_null_sequence() -> None:
    """验证偏好列表不能用 null 清空，应明确传空数组。"""

    repository = AsyncMock(
        spec=StyleProfileRepository,
    )
    repositories = create_repositories(repository)

    async def override_repositories() -> FashionRepositories:
        """提供不应收到无效 PATCH 的假仓库。"""

        return repositories

    application = create_app()
    application.dependency_overrides[
        get_settings
    ] = override_settings
    application.dependency_overrides[
        get_fashion_repositories
    ] = override_repositories
    client = TestClient(application)

    try:
        response = client.patch(
            "/api/v1/style-profile",
            headers={
                "X-User-ID": "user-001",
            },
            json={
                "preferred_styles": None,
            },
        )
    finally:
        application.dependency_overrides.clear()

    assert response.status_code == 422
    repository.get_by_user_id.assert_not_awaited()
    repository.save.assert_not_awaited()


def test_patch_style_profile_returns_conflict_for_stored_state() -> None:
    """验证 PATCH 与已有档案冲突时返回结构化 409。"""

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
    repositories = create_repositories(repository)

    async def override_repositories() -> FashionRepositories:
        """提供已有喜欢风格的假仓库。"""

        return repositories

    application = create_app()
    application.dependency_overrides[
        get_settings
    ] = override_settings
    application.dependency_overrides[
        get_fashion_repositories
    ] = override_repositories
    client = TestClient(application)

    try:
        response = client.patch(
            "/api/v1/style-profile",
            headers={
                "X-User-ID": "user-001",
            },
            json={
                "avoided_styles": [
                    "简约",
                ],
            },
        )
    finally:
        application.dependency_overrides.clear()

    assert response.status_code == 409
    assert response.json() == {
        "code": "style_profile_update_conflict",
        "message": (
            "更新后的档案包含互相冲突的偏好或预算范围"
        ),
    }
    repository.save.assert_not_awaited()


def test_get_preference_candidates_returns_evidence() -> None:
    """验证候选接口返回当前用户的动态风格证据。"""

    style_profile_repository = AsyncMock(
        spec=StyleProfileRepository,
    )
    outfit_repository = AsyncMock(
        spec=OutfitRepository,
    )
    feedback_repository = AsyncMock(
        spec=OutfitFeedbackRepository,
    )
    outfit_repository.get_by_ids.return_value = [
        Outfit(
            outfit_id=outfit_id,
            user_id="user-001",
            name=f"休闲穿搭 {outfit_id}",
            scenario="日常",
            style_tags=(
                "休闲",
            ),
            items=(
                OutfitItem(
                    role="上装",
                    name="测试上装",
                    source="recommendation",
                ),
            ),
            recommendation_reason="候选接口测试。",
        )
        for outfit_id in (
            "outfit-001",
            "outfit-002",
        )
    ]
    feedback_repository.search.return_value = [
        OutfitFeedback(
            user_id="user-001",
            outfit_id=outfit_id,
            sentiment=OutfitFeedbackSentiment.LIKE,
        )
        for outfit_id in (
            "outfit-001",
            "outfit-002",
        )
    ]
    repositories = FashionRepositories(
        style_profiles=style_profile_repository,
        preference_memories=AsyncMock(
            spec=PreferenceMemoryRepository,
        ),
        wardrobe=Mock(),
        outfits=outfit_repository,
        outfit_feedback=feedback_repository,
    )
    async def override_repositories() -> FashionRepositories:
        """提供候选分析使用的假仓库。"""

        return repositories

    application = create_app()
    application.dependency_overrides[
        get_settings
    ] = override_settings
    application.dependency_overrides[
        get_fashion_repositories
    ] = override_repositories
    client = TestClient(application)

    try:
        response = client.get(
            (
                "/api/v1/style-profile/candidates"
                "?minimum_evidence=2"
            ),
            headers={
                "X-User-ID": "user-001",
            },
        )
    finally:
        application.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "candidate_id": create_preference_candidate_id(
                    category=(
                        PreferenceCandidateCategory.STYLE
                    ),
                    value="休闲",
                    direction=PreferenceDirection.PREFER,
                    evidence_outfit_ids=(
                        "outfit-001",
                        "outfit-002",
                    ),
                ),
                "category": "style",
                "source": "outfit_feedback",
                "value": "休闲",
                "direction": "prefer",
                "evidence_count": 2,
                "opposing_evidence_count": 0,
                "evidence_outfit_ids": [
                    "outfit-001",
                    "outfit-002",
                ],
            },
        ],
        "count": 1,
        "minimum_evidence": 2,
    }
    style_profile_repository.save.assert_not_awaited()


def test_confirm_preference_candidate_updates_profile() -> None:
    """验证确认当前候选后合并长期档案并处理互斥风格。"""

    style_profile_repository = AsyncMock(
        spec=StyleProfileRepository,
    )
    style_profile_repository.get_by_user_id.return_value = (
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
    style_profile_repository.save.side_effect = (
        lambda profile: profile
    )
    outfit_repository = AsyncMock(
        spec=OutfitRepository,
    )
    feedback_repository = AsyncMock(
        spec=OutfitFeedbackRepository,
    )
    outfit_repository.get_by_ids.return_value = [
        Outfit(
            outfit_id=outfit_id,
            user_id="user-001",
            name=f"休闲穿搭 {outfit_id}",
            scenario="日常",
            style_tags=(
                "休闲",
            ),
            items=(
                OutfitItem(
                    role="上装",
                    name="测试上装",
                    source="recommendation",
                ),
            ),
            recommendation_reason="候选确认测试。",
        )
        for outfit_id in (
            "outfit-001",
            "outfit-002",
        )
    ]
    feedback_repository.search.return_value = [
        OutfitFeedback(
            user_id="user-001",
            outfit_id=outfit_id,
            sentiment=OutfitFeedbackSentiment.LIKE,
        )
        for outfit_id in (
            "outfit-001",
            "outfit-002",
        )
    ]
    repositories = FashionRepositories(
        style_profiles=style_profile_repository,
        preference_memories=(memory_repository := AsyncMock(
            spec=PreferenceMemoryRepository,
        )),
        wardrobe=Mock(),
        outfits=outfit_repository,
        outfit_feedback=feedback_repository,
    )
    memory_repository.get_by_identity.return_value = None
    memory_repository.save.side_effect = (
        lambda memory: memory
    )

    async def override_repositories() -> FashionRepositories:
        """提供候选确认所需的假仓库。"""

        return repositories

    application = create_app()
    application.dependency_overrides[
        get_settings
    ] = override_settings
    application.dependency_overrides[
        get_fashion_repositories
    ] = override_repositories
    client = TestClient(application)

    try:
        response = client.post(
            "/api/v1/style-profile/candidates/confirm",
            headers={
                "X-User-ID": "user-001",
            },
            json={
                "candidate_id": (
                    create_preference_candidate_id(
                        category=(
                            PreferenceCandidateCategory.STYLE
                        ),
                        value="休闲",
                        direction=(
                            PreferenceDirection.PREFER
                        ),
                        evidence_outfit_ids=(
                            "outfit-001",
                            "outfit-002",
                        ),
                    )
                ),
                "category": "style",
                "value": "休闲",
                "direction": "prefer",
                "minimum_evidence": 2,
            },
        )
    finally:
        application.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["preferred_styles"] == [
        "简约",
        "休闲",
    ]
    assert response.json()["avoided_styles"] == []
    assert "user_id" not in response.json()


def test_confirm_preference_candidate_rejects_stale_candidate() -> None:
    """验证过期候选返回结构化 409 且不会保存档案。"""

    style_profile_repository = AsyncMock(
        spec=StyleProfileRepository,
    )
    outfit_repository = AsyncMock(
        spec=OutfitRepository,
    )
    feedback_repository = AsyncMock(
        spec=OutfitFeedbackRepository,
    )
    feedback_repository.search.return_value = []
    repositories = FashionRepositories(
        style_profiles=style_profile_repository,
        preference_memories=AsyncMock(
            spec=PreferenceMemoryRepository,
        ),
        wardrobe=Mock(),
        outfits=outfit_repository,
        outfit_feedback=feedback_repository,
    )

    async def override_repositories() -> FashionRepositories:
        """提供没有有效候选的假仓库。"""

        return repositories

    application = create_app()
    application.dependency_overrides[
        get_settings
    ] = override_settings
    application.dependency_overrides[
        get_fashion_repositories
    ] = override_repositories
    client = TestClient(application)

    try:
        response = client.post(
            "/api/v1/style-profile/candidates/confirm",
            headers={
                "X-User-ID": "user-001",
            },
            json={
                "candidate_id": ("pc_" + "0" * 32),
                "category": "style",
                "value": "休闲",
                "direction": "prefer",
            },
        )
    finally:
        application.dependency_overrides.clear()

    assert response.status_code == 409
    assert response.json() == {
        "code": "preference_candidate_unavailable",
        "message": (
            "候选偏好已不存在、方向已变化或证据不足"
        ),
    }
    style_profile_repository.save.assert_not_awaited()
