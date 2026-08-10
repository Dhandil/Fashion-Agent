"""批量衣物图片识别 API 集成测试。"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock

from fastapi.testclient import TestClient

from app.api.dependencies.database import get_fashion_repositories
from app.api.dependencies.storage import get_wardrobe_image_storage
from app.api.dependencies.vision import get_wardrobe_image_recognizer
from app.db.repositories.fashion_provider import FashionRepositories
from app.domain.entities.wardrobe_draft import WardrobeItemRecognition
from app.domain.entities.wardrobe_image import WardrobeImageContentType
from app.domain.entities.wardrobe_image_asset import (
    WardrobeImageAsset,
    WardrobeImageAssetStatus,
)
from app.domain.providers.wardrobe_vision import (
    WardrobeImageMultiRecognizer,
    WardrobeImageRecognizer,
)
from app.domain.repositories.wardrobe import WardrobeRepository
from app.domain.repositories.wardrobe_image_asset import (
    WardrobeImageAssetRepository,
)
from app.integrations.storage.local import LocalWardrobeImageStorage
from app.main import create_app


def test_batch_recognition_isolates_single_asset_failure(tmp_path) -> None:
    """验证一个资产失败时，同批其他图片仍返回草稿。"""

    user_id = "batch-user"
    asset_id = "asset-valid"
    image_bytes = b"\xff\xd8\xff" + b"batch-image"
    storage = LocalWardrobeImageStorage(tmp_path)
    storage.write("asset-valid.jpg", image_bytes)
    asset = WardrobeImageAsset(
        image_asset_id=asset_id,
        user_id=user_id,
        object_key="asset-valid.jpg",
        content_type=WardrobeImageContentType.JPEG,
        byte_size=len(image_bytes),
        sha256="a" * 64,
        status=WardrobeImageAssetStatus.UPLOADED,
        created_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )

    image_assets = AsyncMock(spec=WardrobeImageAssetRepository)
    image_assets.get_by_id.side_effect = (
        lambda requested_user, requested_asset: (
            asset
            if requested_user == user_id and requested_asset == asset_id
            else None
        )
    )
    recognizer = AsyncMock(spec=WardrobeImageRecognizer)
    recognizer.recognize.return_value = WardrobeItemRecognition(
        name="浅蓝色衬衫",
        category="衬衫",
        colors=("浅蓝色",),
        confidence=0.9,
    )

    repositories = FashionRepositories(
        style_profiles=Mock(),
        preference_memories=Mock(),
        wardrobe=AsyncMock(spec=WardrobeRepository),
        wardrobe_image_assets=image_assets,
        outfits=Mock(),
        outfit_feedback=Mock(),
    )

    async def override_repositories() -> FashionRepositories:
        return repositories

    application = create_app()
    application.dependency_overrides[get_fashion_repositories] = override_repositories
    application.dependency_overrides[get_wardrobe_image_storage] = lambda: storage
    application.dependency_overrides[get_wardrobe_image_recognizer] = lambda: recognizer

    try:
        with TestClient(application) as client:
            response = client.post(
                "/api/v1/wardrobe/recognitions/batch",
                headers={"X-User-ID": user_id},
                json={"image_asset_ids": [asset_id, "asset-missing"]},
            )
    finally:
        application.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) == 1
    assert payload["items"][0]["image_asset_id"] == asset_id
    assert payload["failures"] == [
        {
            "image_asset_id": "asset-missing",
            "code": "image_asset_not_found",
            "message": "该图片识别失败，请稍后重试或手动录入。",
        },
    ]
    recognizer.recognize.assert_awaited_once()


def test_batch_recognition_splits_multiple_garments_from_one_asset(
    tmp_path,
) -> None:
    """验证一张图片的多个识别结果会分别返回为衣物草稿。"""

    user_id = "multi-garment-user"
    asset_id = "asset-shared"
    image_bytes = b"\xff\xd8\xff" + b"multi-garment-image"
    storage = LocalWardrobeImageStorage(tmp_path)
    storage.write("asset-shared.jpg", image_bytes)
    asset = WardrobeImageAsset(
        image_asset_id=asset_id,
        user_id=user_id,
        object_key="asset-shared.jpg",
        content_type=WardrobeImageContentType.JPEG,
        byte_size=len(image_bytes),
        sha256="b" * 64,
        status=WardrobeImageAssetStatus.UPLOADED,
        created_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )

    image_assets = AsyncMock(spec=WardrobeImageAssetRepository)
    image_assets.get_by_id.return_value = asset
    recognizer = AsyncMock(spec=WardrobeImageMultiRecognizer)
    recognizer.recognize_many.return_value = (
        WardrobeItemRecognition(
            name="浅蓝色衬衫",
            category="衬衫",
            confidence=0.9,
        ),
        WardrobeItemRecognition(
            name="深灰色长裤",
            category="长裤",
            confidence=0.8,
        ),
    )

    repositories = FashionRepositories(
        style_profiles=Mock(),
        preference_memories=Mock(),
        wardrobe=AsyncMock(spec=WardrobeRepository),
        wardrobe_image_assets=image_assets,
        outfits=Mock(),
        outfit_feedback=Mock(),
    )

    async def override_repositories() -> FashionRepositories:
        return repositories

    application = create_app()
    application.dependency_overrides[get_fashion_repositories] = override_repositories
    application.dependency_overrides[get_wardrobe_image_storage] = lambda: storage
    application.dependency_overrides[get_wardrobe_image_recognizer] = lambda: recognizer

    try:
        with TestClient(application) as client:
            response = client.post(
                "/api/v1/wardrobe/recognitions/batch",
                headers={"X-User-ID": user_id},
                json={"image_asset_ids": [asset_id]},
            )
    finally:
        application.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert [item["category"] for item in payload["items"]] == ["衬衫", "长裤"]
    assert len({item["draft_id"] for item in payload["items"]}) == 2
    assert {item["image_asset_id"] for item in payload["items"]} == {asset_id}
    assert payload["failures"] == []
    recognizer.recognize_many.assert_awaited_once()
