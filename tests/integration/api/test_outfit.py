"""用户确认保存 Outfit API 测试。"""

from unittest.mock import (
    AsyncMock,
    Mock,
)
from uuid import UUID

from fastapi.testclient import TestClient

from app.api.dependencies.agent import (
    get_request_shopping_graph,
)
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
from app.domain.entities.outfit import (
    Outfit,
    OutfitItem,
    OutfitRecommendation,
)
from app.domain.repositories.outfit import OutfitRepository
from app.main import create_app


def override_settings() -> Settings:
    """确保测试不读取本地开发环境配置。"""

    return Settings(
        _env_file=None,
        app_env="test",
        debug=False,
    )


def create_saved_outfit() -> Outfit:
    """创建 API 查询测试使用的已保存穿搭。"""

    return Outfit(
        outfit_id="outfit-001",
        user_id="user-001",
        name="夏季通勤搭配",
        scenario="通勤",
        style_tags=[
            "简约",
        ],
        season="夏季",
        items=[
            OutfitItem(
                role="上装",
                name="浅蓝色亚麻衬衫",
                source="wardrobe",
                source_reference_id="shirt-001",
            ),
        ],
        recommendation_reason="优先使用已有衣物。",
    )


def test_confirm_outfit_saves_current_recommendation() -> None:
    """验证确认接口保存当前用户会话中的推荐。"""

    recommendation = OutfitRecommendation(
        name="夏季通勤搭配",
        scenario="通勤",
        items=[
            OutfitItem(
                role="上装",
                name="浅蓝色亚麻衬衫",
                source="wardrobe",
                source_reference_id="shirt-001",
            ),
        ],
        recommendation_reason="优先使用已有衣物。",
    )

    graph = Mock()
    graph.aget_state = AsyncMock(
        return_value=Mock(
            values={
                "outfit_recommendation": recommendation,
            },
        ),
    )

    outfit_repository = AsyncMock(
        spec=OutfitRepository,
    )
    outfit_repository.save.side_effect = (
        lambda outfit: outfit
    )
    repositories = FashionRepositories(
        style_profiles=Mock(),
        wardrobe=Mock(),
        outfits=outfit_repository,
    )

    async def override_repositories() -> FashionRepositories:
        """提供假的 Outfit 仓库。"""

        return repositories

    def override_graph() -> Mock:
        """提供包含待确认推荐的假 Graph。"""

        return graph

    application = create_app()
    application.dependency_overrides[
        get_settings
    ] = override_settings
    application.dependency_overrides[
        get_fashion_repositories
    ] = override_repositories
    application.dependency_overrides[
        get_request_shopping_graph
    ] = override_graph

    client = TestClient(application)

    try:
        response = client.post(
            "/api/v1/outfits",
            headers={
                "X-User-ID": "user-001",
            },
            json={
                "conversation_id": "conversation-001",
            },
        )
    finally:
        application.dependency_overrides.clear()

    assert response.status_code == 201

    response_data = response.json()
    assert UUID(response_data["outfit_id"])
    assert response_data["name"] == "夏季通勤搭配"
    assert response_data["items"][0][
        "source_reference_id"
    ] == "shirt-001"

    # API 不允许响应泄露内部用户 ID
    assert "user_id" not in response_data


def test_confirm_outfit_requires_current_recommendation() -> None:
    """验证当前会话没有推荐时返回结构化 404。"""

    graph = Mock()
    graph.aget_state = AsyncMock(
        return_value=Mock(
            values={
                "outfit_recommendation": None,
            },
        ),
    )
    outfit_repository = AsyncMock(
        spec=OutfitRepository,
    )
    repositories = FashionRepositories(
        style_profiles=Mock(),
        wardrobe=Mock(),
        outfits=outfit_repository,
    )

    async def override_repositories() -> FashionRepositories:
        """提供不会被调用的假 Outfit 仓库。"""

        return repositories

    application = create_app()
    application.dependency_overrides[
        get_settings
    ] = override_settings
    application.dependency_overrides[
        get_fashion_repositories
    ] = override_repositories
    application.dependency_overrides[
        get_request_shopping_graph
    ] = lambda: graph

    client = TestClient(application)

    try:
        response = client.post(
            "/api/v1/outfits",
            headers={
                "X-User-ID": "user-001",
            },
            json={
                "conversation_id": "conversation-without-outfit",
            },
        )
    finally:
        application.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json() == {
        "code": "outfit_recommendation_not_found",
        "message": "当前会话中没有可以保存的穿搭推荐",
    }
    outfit_repository.save.assert_not_awaited()


def test_list_outfits_uses_filters_and_current_user() -> None:
    """验证列表接口只查询当前用户并传递过滤条件。"""

    outfit_repository = AsyncMock(
        spec=OutfitRepository,
    )
    outfit_repository.search.return_value = [
        create_saved_outfit(),
    ]
    repositories = FashionRepositories(
        style_profiles=Mock(),
        wardrobe=Mock(),
        outfits=outfit_repository,
    )

    async def override_repositories() -> FashionRepositories:
        """提供假的查询仓库。"""

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
                "/api/v1/outfits"
                "?scenario=通勤"
                "&favorite_only=true"
                "&limit=10"
            ),
            headers={
                "X-User-ID": "user-001",
            },
        )
    finally:
        application.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["items"][0][
        "outfit_id"
    ] == "outfit-001"
    outfit_repository.search.assert_awaited_once_with(
        user_id="user-001",
        scenario="通勤",
        favorite_only=True,
        limit=10,
    )


def test_get_outfit_returns_current_user_record() -> None:
    """验证详情接口返回当前用户指定的穿搭。"""

    outfit = create_saved_outfit()
    outfit_repository = AsyncMock(
        spec=OutfitRepository,
    )
    outfit_repository.get_by_id.return_value = outfit
    repositories = FashionRepositories(
        style_profiles=Mock(),
        wardrobe=Mock(),
        outfits=outfit_repository,
    )

    async def override_repositories() -> FashionRepositories:
        """提供假的详情查询仓库。"""

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
            "/api/v1/outfits/outfit-001",
            headers={
                "X-User-ID": "user-001",
            },
        )
    finally:
        application.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["name"] == "夏季通勤搭配"
    outfit_repository.get_by_id.assert_awaited_once_with(
        user_id="user-001",
        outfit_id="outfit-001",
    )


def test_get_outfit_returns_structured_not_found() -> None:
    """验证详情不存在时返回结构化 404。"""

    outfit_repository = AsyncMock(
        spec=OutfitRepository,
    )
    outfit_repository.get_by_id.return_value = None
    repositories = FashionRepositories(
        style_profiles=Mock(),
        wardrobe=Mock(),
        outfits=outfit_repository,
    )

    async def override_repositories() -> FashionRepositories:
        """提供返回空结果的假仓库。"""

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
            "/api/v1/outfits/unknown-outfit",
            headers={
                "X-User-ID": "user-001",
            },
        )
    finally:
        application.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json() == {
        "code": "outfit_not_found",
        "message": "未找到指定的穿搭方案",
    }


def test_update_outfit_favorite_uses_current_user() -> None:
    """验证收藏接口只更新当前用户的指定穿搭。"""

    outfit = create_saved_outfit()
    outfit_repository = AsyncMock(
        spec=OutfitRepository,
    )
    outfit_repository.get_by_id.return_value = outfit
    outfit_repository.save.side_effect = (
        lambda updated_outfit: updated_outfit
    )
    repositories = FashionRepositories(
        style_profiles=Mock(),
        wardrobe=Mock(),
        outfits=outfit_repository,
    )

    async def override_repositories() -> FashionRepositories:
        """提供假的收藏更新仓库。"""

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
            "/api/v1/outfits/outfit-001/favorite",
            headers={
                "X-User-ID": "user-001",
            },
            json={
                "is_favorite": True,
            },
        )
    finally:
        application.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["is_favorite"] is True

    outfit_repository.get_by_id.assert_awaited_once_with(
        user_id="user-001",
        outfit_id="outfit-001",
    )
    saved_outfit = (
        outfit_repository.save.await_args.args[0]
    )
    assert saved_outfit.user_id == "user-001"
    assert saved_outfit.is_favorite is True
