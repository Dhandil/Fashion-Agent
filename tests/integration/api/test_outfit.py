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
