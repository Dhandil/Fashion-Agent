"""FastAPI 请求级 Agent 依赖测试。"""

from unittest.mock import Mock, patch

from app.api.dependencies.agent import (
    get_request_shopping_graph,
)
from app.api.dependencies.identity import CurrentUser
from app.db.repositories.fashion_provider import (
    FashionRepositories,
)
from app.domain.providers.weather import WeatherProvider
from app.domain.repositories.outfit import OutfitRepository
from app.domain.repositories.outfit_feedback import (
    OutfitFeedbackRepository,
)
from app.domain.repositories.wardrobe import (
    WardrobeRepository,
)


def test_agent_dependency_uses_current_user_and_wardrobe_repository() -> None:
    """验证 Agent 依赖使用同一请求的身份和衣橱仓库。"""

    current_user = CurrentUser(
        user_id="user-001",
    )
    wardrobe_repository = Mock(
        spec=WardrobeRepository,
    )
    outfit_repository = Mock(
        spec=OutfitRepository,
    )
    feedback_repository = Mock(
        spec=OutfitFeedbackRepository,
    )
    repositories = FashionRepositories(
        style_profiles=(style_profile_repository := Mock()),
        preference_memories=Mock(),
        wardrobe=wardrobe_repository,
        outfits=outfit_repository,
        outfit_feedback=feedback_repository,
    )
    fake_graph = Mock()
    weather_provider = Mock(
        spec=WeatherProvider,
    )

    with patch(
        "app.api.dependencies.agent.create_user_shopping_graph",
        return_value=fake_graph,
    ) as mocked_create_graph:
        graph = get_request_shopping_graph(
            current_user=current_user,
            repositories=repositories,
            weather_provider=weather_provider,
        )

    assert graph is fake_graph
    mocked_create_graph.assert_called_once_with(
        wardrobe_repository=wardrobe_repository,
        outfit_repository=outfit_repository,
        outfit_feedback_repository=feedback_repository,
        style_profile_repository=style_profile_repository,
        user_id="user-001",
        weather_provider=weather_provider,
    )
