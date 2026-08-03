"""衣物照片识别 Provider 配置装配测试。"""

from unittest.mock import patch

import pytest

from app.core.config import Settings
from app.core.exceptions import ConfigurationError
from app.integrations.vision.openai_compatible import (
    OpenAICompatibleWardrobeImageRecognizer,
)
from app.integrations.vision.provider import (
    get_wardrobe_image_recognizer,
)


def test_recognizer_factory_returns_none_when_disabled() -> None:
    """验证默认关闭照片识别时不创建外部适配器。"""

    settings = Settings(
        _env_file=None,
        wardrobe_vision_backend="disabled",
    )
    get_wardrobe_image_recognizer.cache_clear()

    with patch(
        "app.integrations.vision.provider.get_settings",
        return_value=settings,
    ):
        recognizer = get_wardrobe_image_recognizer()

    assert recognizer is None
    get_wardrobe_image_recognizer.cache_clear()


def test_recognizer_factory_builds_openai_compatible_adapter() -> None:
    """验证配置齐全时创建 OpenAI 兼容视觉适配器。"""

    settings = Settings(
        _env_file=None,
        wardrobe_vision_backend="openai_compatible",
        wardrobe_vision_base_url=("https://vision.example.test/v1"),
        wardrobe_vision_api_key="test-key",
        wardrobe_vision_model="test-vision-model",
    )
    get_wardrobe_image_recognizer.cache_clear()

    with patch(
        "app.integrations.vision.provider.get_settings",
        return_value=settings,
    ):
        recognizer = get_wardrobe_image_recognizer()

    assert isinstance(
        recognizer,
        OpenAICompatibleWardrobeImageRecognizer,
    )
    get_wardrobe_image_recognizer.cache_clear()


@pytest.mark.parametrize(
    (
        "missing_setting",
        "expected_message",
    ),
    [
        (
            "wardrobe_vision_base_url",
            "WARDROBE_VISION_BASE_URL",
        ),
        (
            "wardrobe_vision_api_key",
            "WARDROBE_VISION_API_KEY",
        ),
        (
            "wardrobe_vision_model",
            "WARDROBE_VISION_MODEL",
        ),
    ],
)
def test_recognizer_factory_requires_full_configuration(
    missing_setting: str,
    expected_message: str,
) -> None:
    """验证启用识别但配置缺失时给出明确的配置错误。"""

    settings_values: dict[str, object] = {
        "wardrobe_vision_base_url": ("https://vision.example.test/v1"),
        "wardrobe_vision_api_key": "test-key",
        "wardrobe_vision_model": "test-vision-model",
    }
    settings_values[missing_setting] = None
    settings = Settings(
        _env_file=None,
        wardrobe_vision_backend="openai_compatible",
        **settings_values,
    )
    get_wardrobe_image_recognizer.cache_clear()

    with (
        patch(
            "app.integrations.vision.provider.get_settings",
            return_value=settings,
        ),
        pytest.raises(
            ConfigurationError,
            match=expected_message,
        ),
    ):
        get_wardrobe_image_recognizer()

    get_wardrobe_image_recognizer.cache_clear()
