"""用户衣橱 API 集成测试。"""

from unittest.mock import (
    AsyncMock,
    Mock,
    patch,
)
from uuid import UUID

from fastapi.testclient import TestClient

from app.api.dependencies.database import (
    get_fashion_repositories,
)
from app.db.repositories.fashion_provider import (
    FashionRepositories,
)
from app.domain.repositories.wardrobe import (
    WardrobeRepository,
)
from app.main import create_app


def test_create_wardrobe_item_uses_current_user() -> None:
    """验证新增衣物使用身份依赖中的用户 ID。"""

    # 衣橱仓库使用异步 Mock，避免测试访问真实 PostgreSQL
    wardrobe_repository = AsyncMock(
        spec=WardrobeRepository,
    )
    wardrobe_repository.save.side_effect = lambda item: item

    repositories = FashionRepositories(
        style_profiles=Mock(),
        wardrobe=wardrobe_repository,
        outfits=Mock(),
        outfit_feedback=Mock(),
    )

    async def override_repositories() -> FashionRepositories:
        """为本测试提供假的请求级仓库集合。"""

        return repositories

    application = create_app()
    application.dependency_overrides[get_fashion_repositories] = override_repositories
    client = TestClient(application)

    fixed_item_id = UUID(
        "11111111-1111-1111-1111-111111111111",
    )

    try:
        # 固定服务端生成的 UUID，使响应断言保持稳定
        with patch(
            "app.api.routers.wardrobe.uuid4",
            return_value=fixed_item_id,
        ):
            response = client.post(
                "/api/v1/wardrobe",
                headers={
                    "X-User-ID": "user-001",
                },
                json={
                    "name": "浅蓝色亚麻衬衫",
                    "category": "衬衫",
                    "colors": [
                        "浅蓝色",
                    ],
                    "materials": [
                        "亚麻",
                        "棉",
                    ],
                    "status": "available",
                },
            )
    finally:
        # 避免依赖覆盖影响同一进程中的其他测试
        application.dependency_overrides.clear()

    assert response.status_code == 201

    response_data = response.json()
    assert response_data["wardrobe_item_id"] == str(
        fixed_item_id,
    )
    assert response_data["name"] == "浅蓝色亚麻衬衫"
    assert response_data["status"] == "available"

    # 响应不暴露内部用户 ID
    assert "user_id" not in response_data

    wardrobe_repository.save.assert_awaited_once()
    saved_item = wardrobe_repository.save.await_args.args[0]

    # 即使请求体没有 user_id，领域实体仍绑定当前登录用户
    assert saved_item.user_id == "user-001"
    assert saved_item.wardrobe_item_id == str(
        fixed_item_id,
    )
