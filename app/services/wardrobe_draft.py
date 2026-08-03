"""衣物照片识别应用服务。"""

import logging
from uuid import uuid4

from app.core.exceptions import (
    WardrobeVisionUnavailableError,
)
from app.core.observability import (
    anonymize_identifier,
    observe_operation,
)
from app.domain.entities.wardrobe_draft import (
    WardrobeItemDraft,
)
from app.domain.entities.wardrobe_image import (
    WardrobeImageContentType,
)
from app.domain.policies.wardrobe_draft import (
    build_wardrobe_item_draft,
)
from app.domain.policies.wardrobe_image import (
    decode_wardrobe_image,
    validate_wardrobe_image,
)
from app.domain.providers.wardrobe_vision import (
    WardrobeImageRecognizer,
)

logger = logging.getLogger(__name__)


async def recognize_wardrobe_image(
    *,
    recognizer: WardrobeImageRecognizer | None,
    user_id: str,
    image_base64: str,
    content_type: WardrobeImageContentType,
    max_image_bytes: int,
    min_confidence: float,
    image_url: str | None = None,
    hint: str | None = None,
) -> WardrobeItemDraft:
    """识别一张衣物照片，返回等待用户确认的草稿。

    草稿不会写入衣橱。用户确认或修正后，仍需通过新增衣橱单品接口
    显式创建正式记录。
    """

    if recognizer is None:
        # 未启用时明确失败，不返回空草稿伪装成识别成功
        raise WardrobeVisionUnavailableError(
            "当前部署未启用衣物照片识别，请手动录入衣橱单品。",
        )

    image = decode_wardrobe_image(
        image_base64=image_base64,
        content_type=content_type,
    )
    validate_wardrobe_image(
        image=image,
        max_bytes=max_image_bytes,
    )

    with observe_operation(
        logger,
        "service.wardrobe_image_recognition",
        # 日志只保留匿名用户标识、格式和体积，不记录照片和识别文本
        user=anonymize_identifier(user_id),
        content_type=image.content_type.value,
        image_bytes=len(image.content),
    ) as observation:
        with observe_operation(
            logger,
            "provider.wardrobe_vision",
            provider_type=(type(recognizer).__name__),
        ):
            recognition = await recognizer.recognize(
                image,
                hint,
            )

        draft = build_wardrobe_item_draft(
            draft_id=str(uuid4()),
            recognition=recognition,
            image_url=image_url,
            min_confidence=min_confidence,
        )
        observation.add_fields(
            confidence=draft.confidence,
            uncertain_field_count=len(
                draft.uncertain_fields,
            ),
            missing_field_count=len(
                draft.missing_fields,
            ),
        )

    return draft
