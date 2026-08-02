"""Outfit 用户反馈 API 测试。"""

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
from app.main import create_app


def override_settings() -> Settings:
    """确保测试不读取本地开发环境配置。"""

    return Settings(
        _env_file=None,
        app_env="test",
        debug=False,
    )


def create_saved_outfit() -> Outfit:
    """创建 API 测试使用的已保存 Outfit。"""

    return Outfit(
        outfit_id="outfit-001",
        user_id="user-001",
        name="夏季通勤搭配",
        scenario="通勤",
        items=(
            OutfitItem(
                role="上装",
                name="浅蓝色亚麻衬衫",
                source="wardrobe",
                source_reference_id="shirt-001",
            ),
        ),
        recommendation_reason="优先使用已有衣物。",
    )


def create_repositories(
    outfit_repository: OutfitRepository,
    feedback_repository: OutfitFeedbackRepository,
) -> FashionRepositories:
    """组合反馈 API 测试所需的假仓库。"""

    return FashionRepositories(
        style_profiles=Mock(),
        preference_memories=Mock(),
        wardrobe=Mock(),
        outfits=outfit_repository,
        outfit_feedback=feedback_repository,
    )


def test_upsert_outfit_feedback_uses_current_user() -> None:
    """验证反馈接口使用当前用户身份并返回规范化结果。"""

    outfit_repository = AsyncMock(
        spec=OutfitRepository,
    )
    outfit_repository.get_by_id.return_value = (
        create_saved_outfit()
    )
    feedback_repository = AsyncMock(
        spec=OutfitFeedbackRepository,
    )
    feedback_repository.save.side_effect = (
        lambda feedback: feedback
    )
    repositories = create_repositories(
        outfit_repository,
        feedback_repository,
    )

    async def override_repositories() -> FashionRepositories:
        """提供假的 Outfit 与反馈仓库。"""

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
            "/api/v1/outfits/outfit-001/feedback",
            headers={
                "X-User-ID": "user-001",
            },
            json={
                "sentiment": "like",
                "comment": "  配色很适合我  ",
            },
        )
    finally:
        application.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "outfit_id": "outfit-001",
        "sentiment": "like",
        "comment": "配色很适合我",
    }

    saved_feedback = (
        feedback_repository.save.await_args.args[0]
    )
    assert saved_feedback.user_id == "user-001"
    assert saved_feedback.sentiment == (
        OutfitFeedbackSentiment.LIKE
    )


def test_upsert_outfit_feedback_requires_content() -> None:
    """验证空反馈在进入服务和仓库之前被拒绝。"""

    outfit_repository = AsyncMock(
        spec=OutfitRepository,
    )
    feedback_repository = AsyncMock(
        spec=OutfitFeedbackRepository,
    )
    repositories = create_repositories(
        outfit_repository,
        feedback_repository,
    )

    async def override_repositories() -> FashionRepositories:
        """提供不应该被调用的假仓库。"""

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
            "/api/v1/outfits/outfit-001/feedback",
            headers={
                "X-User-ID": "user-001",
            },
            json={
                "comment": "   ",
            },
        )
    finally:
        application.dependency_overrides.clear()

    assert response.status_code == 422
    outfit_repository.get_by_id.assert_not_awaited()
    feedback_repository.save.assert_not_awaited()


def test_get_outfit_feedback_returns_current_feedback() -> None:
    """验证反馈查询接口只读取当前用户的数据。"""

    outfit_repository = AsyncMock(
        spec=OutfitRepository,
    )
    outfit_repository.get_by_id.return_value = (
        create_saved_outfit()
    )
    feedback_repository = AsyncMock(
        spec=OutfitFeedbackRepository,
    )
    feedback_repository.get_by_outfit_id.return_value = (
        OutfitFeedback(
            user_id="user-001",
            outfit_id="outfit-001",
            sentiment=OutfitFeedbackSentiment.DISLIKE,
            comment="裤子颜色太深",
        )
    )
    repositories = create_repositories(
        outfit_repository,
        feedback_repository,
    )

    async def override_repositories() -> FashionRepositories:
        """提供假的 Outfit 与反馈仓库。"""

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
            "/api/v1/outfits/outfit-001/feedback",
            headers={
                "X-User-ID": "user-001",
            },
        )
    finally:
        application.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["sentiment"] == "dislike"
    assert "user_id" not in response.json()
    feedback_repository.get_by_outfit_id.assert_awaited_once_with(
        user_id="user-001",
        outfit_id="outfit-001",
    )


def test_get_outfit_feedback_returns_structured_not_found() -> None:
    """验证 Outfit 尚无反馈时返回结构化 404。"""

    outfit_repository = AsyncMock(
        spec=OutfitRepository,
    )
    outfit_repository.get_by_id.return_value = (
        create_saved_outfit()
    )
    feedback_repository = AsyncMock(
        spec=OutfitFeedbackRepository,
    )
    feedback_repository.get_by_outfit_id.return_value = None
    repositories = create_repositories(
        outfit_repository,
        feedback_repository,
    )

    async def override_repositories() -> FashionRepositories:
        """提供返回空反馈的假仓库。"""

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
            "/api/v1/outfits/outfit-001/feedback",
            headers={
                "X-User-ID": "user-001",
            },
        )
    finally:
        application.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json() == {
        "code": "outfit_feedback_not_found",
        "message": "当前穿搭方案还没有用户反馈",
    }


def test_list_recent_outfit_feedback_returns_outfit_summary() -> None:
    """验证最近反馈接口返回原 Outfit 摘要并传递筛选条件。"""

    outfit = create_saved_outfit()
    feedback = OutfitFeedback(
        user_id="user-001",
        outfit_id="outfit-001",
        sentiment=OutfitFeedbackSentiment.LIKE,
        comment="喜欢清爽配色",
    )
    outfit_repository = AsyncMock(
        spec=OutfitRepository,
    )
    outfit_repository.get_by_ids.return_value = [
        outfit,
    ]
    feedback_repository = AsyncMock(
        spec=OutfitFeedbackRepository,
    )
    feedback_repository.search.return_value = [
        feedback,
    ]
    repositories = create_repositories(
        outfit_repository,
        feedback_repository,
    )

    async def override_repositories() -> FashionRepositories:
        """提供最近反馈查询所需的假仓库。"""

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
                "/api/v1/outfits/feedback/recent"
                "?sentiment=like&limit=10"
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
                "outfit_id": "outfit-001",
                "outfit_name": "夏季通勤搭配",
                "scenario": "通勤",
                "sentiment": "like",
                "comment": "喜欢清爽配色",
            },
        ],
        "count": 1,
        "limit": 10,
    }
    feedback_repository.search.assert_awaited_once_with(
        user_id="user-001",
        sentiment=OutfitFeedbackSentiment.LIKE,
        limit=10,
    )


def test_delete_outfit_feedback_returns_no_content() -> None:
    """验证撤回反馈接口删除当前用户记录并返回 204。"""

    outfit_repository = AsyncMock(
        spec=OutfitRepository,
    )
    outfit_repository.get_by_id.return_value = (
        create_saved_outfit()
    )
    feedback_repository = AsyncMock(
        spec=OutfitFeedbackRepository,
    )
    feedback_repository.delete.return_value = True
    repositories = create_repositories(
        outfit_repository,
        feedback_repository,
    )

    async def override_repositories() -> FashionRepositories:
        """提供反馈删除所需的假仓库。"""

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
        response = client.delete(
            "/api/v1/outfits/outfit-001/feedback",
            headers={
                "X-User-ID": "user-001",
            },
        )
    finally:
        application.dependency_overrides.clear()

    assert response.status_code == 204
    assert response.content == b""
    feedback_repository.delete.assert_awaited_once_with(
        user_id="user-001",
        outfit_id="outfit-001",
    )
