from pathlib import Path

import httpx
import pytest

from scripts.smoke_wardrobe_vision import (
    VisionSmokeError,
    detect_content_type,
    run_vision_smoke,
    validate_draft_payload,
)


def test_detect_content_type_accepts_jpeg_and_png(tmp_path: Path) -> None:
    assert detect_content_type(tmp_path / "shirt.jpg") == "image/jpeg"
    assert detect_content_type(tmp_path / "shirt.png") == "image/png"


def test_detect_content_type_rejects_webp(tmp_path: Path) -> None:
    with pytest.raises(VisionSmokeError):
        detect_content_type(tmp_path / "shirt.webp")


def test_validate_draft_payload_returns_safe_summary() -> None:
    result = validate_draft_payload(
        {
            "draft_id": "draft-1",
            "confidence": 0.82,
            "missing_fields": ["materials"],
            "uncertain_fields": ["category"],
        },
    )

    assert result.draft_id == "draft-1"
    assert result.confidence == 0.82
    assert result.missing_fields == ("materials",)
    assert result.uncertain_fields == ("category",)


def test_run_vision_smoke_posts_image_without_persisting_response(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "shirt.jpg"
    image_path.write_bytes(b"fake-jpeg")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/wardrobe/recognitions"
        assert request.headers["X-User-ID"] == "smoke-user"
        payload = request.read().decode("utf-8")
        assert "image_base64" in payload
        return httpx.Response(
            200,
            json={
                "draft_id": "draft-1",
                "confidence": 0.9,
                "missing_fields": [],
                "uncertain_fields": [],
            },
        )

    result = run_vision_smoke(
        image_path=image_path,
        base_url="http://testserver",
        user_id="smoke-user",
        timeout=10,
        transport=httpx.MockTransport(handler),
    )

    assert result.draft_id == "draft-1"
