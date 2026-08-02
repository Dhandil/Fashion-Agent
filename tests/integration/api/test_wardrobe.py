"""用户衣橱 API 集成测试。"""

from collections.abc import Iterator
from contextlib import contextmanager
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
from app.domain.entities.wardrobe_item import (
    WardrobeItem,
    WardrobeItemStatus,
)
from app.domain.repositories.wardrobe import (
    WardrobeRepository,
)
from app.main import create_app


def create_test_item(
    status: WardrobeItemStatus = (
        WardrobeItemStatus.AVAILABLE
    ),
) -> WardrobeItem:
    """创建衣橱 API 测试复用的领域实体。"""

    return WardrobeItem(
        wardrobe_item_id="wardrobe-001",
        user_id="user-001",
        name="浅蓝色亚麻衬衫",
        category="衬衫",
        colors=(
            "浅蓝色",
        ),
        materials=(
            "亚麻",
        ),
        status=status,
        notes="低温清洗",
    )


@contextmanager
def wardrobe_test_client(
    repository: WardrobeRepository,
) -> Iterator[TestClient]:
    """创建注入假衣橱仓库的 API 测试客户端。"""

    repositories = FashionRepositories(
        style_profiles=Mock(),
        preference_memories=Mock(),
        wardrobe=repository,
        outfits=Mock(),
        outfit_feedback=Mock(),
    )

    async def override_repositories() -> FashionRepositories:
        """为当前测试提供假的请求级仓库集合。"""

        return repositories

    application = create_app()
    application.dependency_overrides[
        get_fashion_repositories
    ] = override_repositories

    try:
        with TestClient(application) as client:
            yield client
    finally:
        application.dependency_overrides.clear()


def test_create_wardrobe_item_uses_current_user() -> None:
    """验证新增衣物使用身份依赖中的用户 ID。"""

    # 衣橱仓库使用异步 Mock，避免测试访问真实 PostgreSQL
    wardrobe_repository = AsyncMock(
        spec=WardrobeRepository,
    )
    wardrobe_repository.save.side_effect = lambda item: item

    repositories = FashionRepositories(
        style_profiles=Mock(),
        preference_memories=Mock(),
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


def test_list_wardrobe_items_returns_filtered_page() -> None:
    """验证衣橱列表返回过滤条件对应的分页结果。"""

    repository = AsyncMock(
        spec=WardrobeRepository,
    )
    repository.search.return_value = [
        create_test_item(),
    ]
    repository.count.return_value = 3

    with wardrobe_test_client(repository) as client:
        response = client.get(
            (
                "/api/v1/wardrobe"
                "?category=衬衫"
                "&status=available"
                "&limit=1"
                "&offset=1"
            ),
            headers={
                "X-User-ID": "user-001",
            },
        )

    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["total"] == 3
    assert response.json()["limit"] == 1
    assert response.json()["offset"] == 1
    assert response.json()["items"][0]["name"] == (
        "浅蓝色亚麻衬衫"
    )
    assert (
        "user_id"
        not in response.json()["items"][0]
    )
    repository.search.assert_awaited_once_with(
        user_id="user-001",
        category="衬衫",
        status=WardrobeItemStatus.AVAILABLE,
        limit=1,
        offset=1,
    )


def test_get_wardrobe_item_returns_current_user_item() -> None:
    """验证详情接口读取当前用户的指定衣物。"""

    repository = AsyncMock(
        spec=WardrobeRepository,
    )
    repository.get_by_id.return_value = (
        create_test_item()
    )

    with wardrobe_test_client(repository) as client:
        response = client.get(
            "/api/v1/wardrobe/wardrobe-001",
            headers={
                "X-User-ID": "user-001",
            },
        )

    assert response.status_code == 200
    assert response.json()["wardrobe_item_id"] == (
        "wardrobe-001"
    )
    repository.get_by_id.assert_awaited_once_with(
        user_id="user-001",
        wardrobe_item_id="wardrobe-001",
    )


def test_get_wardrobe_item_returns_structured_not_found() -> None:
    """验证不存在或属于其他用户的衣物统一返回 404。"""

    repository = AsyncMock(
        spec=WardrobeRepository,
    )
    repository.get_by_id.return_value = None

    with wardrobe_test_client(repository) as client:
        response = client.get(
            "/api/v1/wardrobe/other-user-item",
            headers={
                "X-User-ID": "user-001",
            },
        )

    assert response.status_code == 404
    assert response.json() == {
        "code": "wardrobe_item_not_found",
        "message": "未找到指定的衣橱单品",
    }


def test_patch_wardrobe_item_preserves_omitted_fields() -> None:
    """验证局部修改不会清空未提供的衣物信息。"""

    repository = AsyncMock(
        spec=WardrobeRepository,
    )
    repository.get_by_id.return_value = (
        create_test_item()
    )
    repository.save.side_effect = (
        lambda item: item
    )

    with wardrobe_test_client(repository) as client:
        response = client.patch(
            "/api/v1/wardrobe/wardrobe-001",
            headers={
                "X-User-ID": "user-001",
            },
            json={
                "notes": "只修改这条说明",
            },
        )

    assert response.status_code == 200
    assert response.json()["name"] == (
        "浅蓝色亚麻衬衫"
    )
    assert response.json()["colors"] == [
        "浅蓝色",
    ]
    assert response.json()["notes"] == (
        "只修改这条说明"
    )


def test_patch_wardrobe_item_rejects_null_sequence() -> None:
    """验证序列字段不能使用 null 清空。"""

    repository = AsyncMock(
        spec=WardrobeRepository,
    )

    with wardrobe_test_client(repository) as client:
        response = client.patch(
            "/api/v1/wardrobe/wardrobe-001",
            headers={
                "X-User-ID": "user-001",
            },
            json={
                "colors": None,
            },
        )

    assert response.status_code == 422
    repository.get_by_id.assert_not_awaited()
    repository.save.assert_not_awaited()


def test_set_wardrobe_item_status_updates_availability() -> None:
    """验证状态开关可以把衣物设为暂不可用。"""

    repository = AsyncMock(
        spec=WardrobeRepository,
    )
    repository.get_by_id.return_value = (
        create_test_item()
    )
    repository.save.side_effect = (
        lambda item: item
    )

    with wardrobe_test_client(repository) as client:
        response = client.patch(
            (
                "/api/v1/wardrobe/"
                "wardrobe-001/status"
            ),
            headers={
                "X-User-ID": "user-001",
            },
            json={
                "status": "unavailable",
            },
        )

    assert response.status_code == 200
    assert response.json()["status"] == (
        "unavailable"
    )
    saved_item = repository.save.await_args.args[0]
    assert (
        saved_item.status
        is WardrobeItemStatus.UNAVAILABLE
    )


def test_delete_wardrobe_item_returns_no_content() -> None:
    """验证删除成功后返回 204 且不返回响应体。"""

    repository = AsyncMock(
        spec=WardrobeRepository,
    )
    repository.delete.return_value = True

    with wardrobe_test_client(repository) as client:
        response = client.delete(
            "/api/v1/wardrobe/wardrobe-001",
            headers={
                "X-User-ID": "user-001",
            },
        )

    assert response.status_code == 204
    assert response.content == b""
    repository.delete.assert_awaited_once_with(
        user_id="user-001",
        wardrobe_item_id="wardrobe-001",
    )


def test_delete_missing_wardrobe_item_returns_not_found() -> None:
    """验证删除不存在的衣物返回结构化 404。"""

    repository = AsyncMock(
        spec=WardrobeRepository,
    )
    repository.delete.return_value = False

    with wardrobe_test_client(repository) as client:
        response = client.delete(
            "/api/v1/wardrobe/missing-item",
            headers={
                "X-User-ID": "user-001",
            },
        )

    assert response.status_code == 404
    assert response.json()["code"] == (
        "wardrobe_item_not_found"
    )
