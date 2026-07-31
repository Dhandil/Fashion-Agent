"""用户长期穿搭档案 API 测试。"""

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
from app.domain.repositories.outfit import OutfitRepository
from app.domain.repositories.outfit_feedback import (
    OutfitFeedbackRepository,
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
        wardrobe=Mock(),
        outfits=Mock(),
        outfit_feedback=Mock(),
    )


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
                "category": "style",
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
