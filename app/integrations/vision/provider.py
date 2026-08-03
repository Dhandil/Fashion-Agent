"""衣物照片识别 Provider 的配置装配。"""

from functools import lru_cache

from app.core.config import get_settings
from app.core.exceptions import ConfigurationError
from app.domain.providers.wardrobe_vision import (
    WardrobeImageRecognizer,
)
from app.integrations.vision.openai_compatible import (
    OpenAICompatibleWardrobeImageRecognizer,
)


@lru_cache
def get_wardrobe_image_recognizer() -> WardrobeImageRecognizer | None:
    """根据配置创建可选的衣物照片识别 Provider。"""

    settings = get_settings()
    if settings.wardrobe_vision_backend == "disabled":
        return None

    if settings.wardrobe_vision_base_url is None:
        raise ConfigurationError(
            "启用衣物照片识别时必须配置 WARDROBE_VISION_BASE_URL",
        )

    if settings.wardrobe_vision_api_key is None:
        raise ConfigurationError(
            "启用衣物照片识别时必须配置 WARDROBE_VISION_API_KEY",
        )

    if settings.wardrobe_vision_model is None:
        raise ConfigurationError(
            "启用衣物照片识别时必须配置 WARDROBE_VISION_MODEL",
        )

    return OpenAICompatibleWardrobeImageRecognizer(
        base_url=settings.wardrobe_vision_base_url,
        api_key=(settings.wardrobe_vision_api_key.get_secret_value()),
        model=settings.wardrobe_vision_model,
        timeout_seconds=(settings.wardrobe_vision_timeout_seconds),
    )
