"""FastAPI 请求级 Agent 依赖。"""

from typing import Annotated

from fastapi import Depends

from app.agents.graphs.shopping import ShoppingGraph
from app.api.dependencies.database import (
    FashionRepositoriesDependency,
)
from app.api.dependencies.identity import (
    CurrentUserDependency,
)
from app.api.dependencies.weather import (
    WeatherProviderDependency,
)
from app.services.agent import (
    create_user_shopping_graph,
)


def get_request_shopping_graph(
    current_user: CurrentUserDependency,
    repositories: FashionRepositoriesDependency,
    weather_provider: WeatherProviderDependency,
) -> ShoppingGraph:
    """为当前用户装配带衣橱访问能力的 Agent Graph。"""

    return create_user_shopping_graph(
        wardrobe_repository=repositories.wardrobe,
        outfit_repository=repositories.outfits,
        outfit_feedback_repository=(repositories.outfit_feedback),
        style_profile_repository=(repositories.style_profiles),
        user_id=current_user.user_id,
        weather_provider=weather_provider,
    )


# 聊天路由通过这个类型获得当前请求专用的 Agent Graph
RequestShoppingGraph = Annotated[
    ShoppingGraph,
    Depends(get_request_shopping_graph),
]
