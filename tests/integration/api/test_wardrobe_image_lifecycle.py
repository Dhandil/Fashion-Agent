"""衣物私有图片上传、确认、读取和关联闭环测试。"""

from collections.abc import Iterator
from contextlib import contextmanager
from unittest.mock import AsyncMock, Mock

from fastapi.testclient import TestClient

from app.api.dependencies.database import get_fashion_repositories
from app.api.dependencies.storage import get_wardrobe_image_storage
from app.db.repositories.fashion_provider import FashionRepositories
from app.domain.entities.wardrobe_image_asset import WardrobeImageAsset
from app.domain.entities.wardrobe_item import WardrobeItem
from app.domain.repositories.wardrobe import WardrobeRepository
from app.domain.repositories.wardrobe_image_asset import (
    WardrobeImageAssetRepository,
)
from app.integrations.storage.local import LocalWardrobeImageStorage
from app.main import create_app


@contextmanager
def lifecycle_client(
    tmp_path,
) -> Iterator[tuple[TestClient, dict[str, WardrobeImageAsset], AsyncMock]]:
    """创建使用临时文件卷和内存字典模拟资产仓库的客户端。"""

    assets: dict[str, WardrobeImageAsset] = {}
    image_assets = AsyncMock(spec=WardrobeImageAssetRepository)

    async def get_asset(user_id: str, image_asset_id: str) -> WardrobeImageAsset | None:
        asset = assets.get(image_asset_id)
        return asset if asset is not None and asset.user_id == user_id else None

    async def save_asset(asset: WardrobeImageAsset) -> WardrobeImageAsset:
        assets[asset.image_asset_id] = asset
        return asset

    image_assets.get_by_id.side_effect = get_asset
    image_assets.save.side_effect = save_asset

    wardrobe = AsyncMock(spec=WardrobeRepository)
    wardrobe.save.side_effect = lambda item: item
    wardrobe.get_by_id.return_value = WardrobeItem(
        wardrobe_item_id="wardrobe-001",
        user_id="lifecycle-user",
        name="浅蓝色衬衫",
        category="衬衫",
        image_asset_id="asset-placeholder",
    )
    wardrobe.delete.return_value = True

    repositories = FashionRepositories(
        style_profiles=Mock(),
        preference_memories=Mock(),
        wardrobe=wardrobe,
        wardrobe_image_assets=image_assets,
        outfits=Mock(),
        outfit_feedback=Mock(),
    )

    async def override_repositories() -> FashionRepositories:
        return repositories

    storage = LocalWardrobeImageStorage(tmp_path)
    application = create_app()
    application.dependency_overrides[get_fashion_repositories] = override_repositories
    application.dependency_overrides[get_wardrobe_image_storage] = lambda: storage

    try:
        with TestClient(application) as client:
            yield client, assets, wardrobe
    finally:
        application.dependency_overrides.clear()


def test_upload_complete_read_and_attach_private_image(tmp_path) -> None:
    """验证图片从上传到衣橱关联的闭环和用户隔离。"""

    image_bytes = b"\xff\xd8\xff" + b"image-content"
    headers = {"X-User-ID": "lifecycle-user"}

    with lifecycle_client(tmp_path) as (client, assets, wardrobe):
        upload = client.post(
            "/api/v1/wardrobe/images/uploads",
            headers=headers,
            json={"content_type": "image/jpeg", "byte_size": len(image_bytes)},
        )
        assert upload.status_code == 201
        asset_id = upload.json()["image_asset_id"]

        uploaded = client.put(
            upload.json()["upload_url"],
            headers={**headers, "Content-Type": "image/jpeg"},
            content=image_bytes,
        )
        assert uploaded.status_code == 204

        complete = client.post(
            f"/api/v1/wardrobe/images/{asset_id}/complete",
            headers=headers,
        )
        assert complete.status_code == 200
        assert complete.json()["status"] == "uploaded"
        assert complete.json()["sha256"]

        content = client.get(
            f"/api/v1/wardrobe/images/{asset_id}/content",
            headers=headers,
        )
        assert content.status_code == 200
        assert content.content == image_bytes

        forbidden = client.get(
            f"/api/v1/wardrobe/images/{asset_id}/content",
            headers={"X-User-ID": "another-user"},
        )
        assert forbidden.status_code == 404

        create_item = client.post(
            "/api/v1/wardrobe",
            headers=headers,
            json={
                "name": "浅蓝色衬衫",
                "category": "衬衫",
                "image_asset_id": asset_id,
            },
        )
        assert create_item.status_code == 201
        assert assets[asset_id].status.value == "attached"

        wardrobe.get_by_id.return_value = WardrobeItem(
            wardrobe_item_id="wardrobe-001",
            user_id="lifecycle-user",
            name="浅蓝色衬衫",
            category="衬衫",
            image_asset_id=asset_id,
        )
        deleted = client.delete(
            "/api/v1/wardrobe/wardrobe-001",
            headers=headers,
        )
        assert deleted.status_code == 204
        assert assets[asset_id].status.value == "deletion_pending"
