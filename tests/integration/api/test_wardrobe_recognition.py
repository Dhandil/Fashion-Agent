"""衣物照片识别 API 集成测试。"""

from base64 import b64encode
from collections.abc import Iterator
from contextlib import contextmanager
from unittest.mock import AsyncMock, Mock

from fastapi.testclient import TestClient

from app.api.dependencies.database import (
    get_fashion_repositories,
)
from app.db.repositories.fashion_provider import (
    FashionRepositories,
)
from app.domain.entities.wardrobe_draft import (
    WardrobeItemRecognition,
)
from app.domain.providers.wardrobe_vision import (
    WardrobeImageRecognizer,
)
from app.domain.repositories.wardrobe import (
    WardrobeRepository,
)
from app.integrations.vision.provider import (
    get_wardrobe_image_recognizer,
)
from app.main import create_app

# 合法 JPEG 文件头，识别结果由测试替身提供
TEST_IMAGE_BASE64 = b64encode(
    b"\xff\xd8\xff" + b"\x01" * 12,
).decode("ascii")


@contextmanager
def recognition_test_client(
    recognizer: WardrobeImageRecognizer | None,
    wardrobe_repository: AsyncMock,
) -> Iterator[TestClient]:
    """创建注入假识别 Provider 和假衣橱仓库的测试客户端。"""

    repositories = FashionRepositories(
        style_profiles=Mock(),
        preference_memories=Mock(),
        wardrobe=wardrobe_repository,
        outfits=Mock(),
        outfit_feedback=Mock(),
    )

    async def override_repositories() -> FashionRepositories:
        """为当前测试提供假的请求级仓库集合。"""

        return repositories

    def override_recognizer() -> (WardrobeImageRecognizer | None):
        """为当前测试提供假的照片识别 Provider。"""

        return recognizer

    application = create_app()
    application.dependency_overrides[get_fashion_repositories] = override_repositories
    application.dependency_overrides[get_wardrobe_image_recognizer] = override_recognizer

    try:
        with TestClient(application) as client:
            yield client
    finally:
        application.dependency_overrides.clear()


def create_recognizer(
    recognition: WardrobeItemRecognition,
) -> AsyncMock:
    """创建返回固定识别结果的 Provider 替身。"""

    recognizer = AsyncMock(
        spec=WardrobeImageRecognizer,
    )
    recognizer.recognize.return_value = recognition
    return recognizer


def test_recognition_returns_draft_and_does_not_write_wardrobe() -> None:
    """验证识别接口只返回待确认草稿，不写入衣橱。"""

    wardrobe_repository = AsyncMock(
        spec=WardrobeRepository,
    )
    recognizer = create_recognizer(
        WardrobeItemRecognition(
            name="浅蓝色亚麻衬衫",
            category="衬衫",
            colors=(
                "浅蓝色",
            ),
            materials=(
                "亚麻",
            ),
            uncertain_fields=(
                "materials",
            ),
            confidence=0.82,
        ),
    )

    with recognition_test_client(
        recognizer=recognizer,
        wardrobe_repository=wardrobe_repository,
    ) as client:
        response = client.post(
            "/api/v1/wardrobe/recognitions",
            headers={
                "X-User-ID": "user-001",
            },
            json={
                "image_base64": TEST_IMAGE_BASE64,
                "content_type": "image/jpeg",
                "image_url": ("https://example.test/item.jpg"),
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "浅蓝色亚麻衬衫"
    assert payload["category"] == "衬衫"
    assert payload["uncertain_fields"] == [
        "materials",
    ]
    assert payload["missing_fields"] == []
    assert payload["unrecognizable_fields"] == [
        "brand",
        "size",
    ]
    assert payload["requires_confirmation"] is True
    assert payload["draft_id"]

    # 草稿不是衣橱事实，识别过程不能产生任何写入
    wardrobe_repository.save.assert_not_awaited()


def test_recognition_returns_503_when_disabled() -> None:
    """验证未启用照片识别时返回明确的 503。"""

    wardrobe_repository = AsyncMock(
        spec=WardrobeRepository,
    )

    with recognition_test_client(
        recognizer=None,
        wardrobe_repository=wardrobe_repository,
    ) as client:
        response = client.post(
            "/api/v1/wardrobe/recognitions",
            headers={
                "X-User-ID": "user-001",
            },
            json={
                "image_base64": TEST_IMAGE_BASE64,
                "content_type": "image/jpeg",
            },
        )

    assert response.status_code == 503
    assert response.json()["code"] == "wardrobe_vision_unavailable"


def test_recognition_rejects_mismatched_image_format() -> None:
    """验证声明格式与实际字节不一致时返回结构化 400。"""

    wardrobe_repository = AsyncMock(
        spec=WardrobeRepository,
    )
    recognizer = create_recognizer(
        WardrobeItemRecognition(
            confidence=0.9,
        ),
    )

    with recognition_test_client(
        recognizer=recognizer,
        wardrobe_repository=wardrobe_repository,
    ) as client:
        response = client.post(
            "/api/v1/wardrobe/recognitions",
            headers={
                "X-User-ID": "user-001",
            },
            json={
                "image_base64": TEST_IMAGE_BASE64,
                "content_type": "image/png",
            },
        )

    assert response.status_code == 400
    assert response.json()["code"] == "wardrobe_image_invalid"
    recognizer.recognize.assert_not_awaited()


def test_recognition_rejects_unsupported_content_type() -> None:
    """验证不支持的图片格式在请求校验阶段被拒绝。"""

    wardrobe_repository = AsyncMock(
        spec=WardrobeRepository,
    )
    recognizer = create_recognizer(
        WardrobeItemRecognition(
            confidence=0.9,
        ),
    )

    with recognition_test_client(
        recognizer=recognizer,
        wardrobe_repository=wardrobe_repository,
    ) as client:
        response = client.post(
            "/api/v1/wardrobe/recognitions",
            headers={
                "X-User-ID": "user-001",
            },
            json={
                "image_base64": TEST_IMAGE_BASE64,
                "content_type": "image/gif",
            },
        )

    assert response.status_code == 422
    recognizer.recognize.assert_not_awaited()


def test_recognition_requires_user_identity() -> None:
    """验证缺少用户身份时不会调用外部识别服务。"""

    wardrobe_repository = AsyncMock(
        spec=WardrobeRepository,
    )
    recognizer = create_recognizer(
        WardrobeItemRecognition(
            confidence=0.9,
        ),
    )

    with recognition_test_client(
        recognizer=recognizer,
        wardrobe_repository=wardrobe_repository,
    ) as client:
        response = client.post(
            "/api/v1/wardrobe/recognitions",
            json={
                "image_base64": TEST_IMAGE_BASE64,
                "content_type": "image/jpeg",
            },
        )

    assert response.status_code == 422
    recognizer.recognize.assert_not_awaited()
