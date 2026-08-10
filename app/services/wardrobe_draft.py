"""衣物照片识别应用服务。"""

import logging
from uuid import uuid4

from app.core.exceptions import (
    WardrobeVisionProviderError,
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
    WardrobeImage,
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
    image_asset_id: str | None = None,
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
            image_asset_id=image_asset_id,
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


async def recognize_wardrobe_image_content(
    *,
    recognizer: WardrobeImageRecognizer | None,
    user_id: str,
    image: WardrobeImage,
    max_image_bytes: int,
    min_confidence: float,
    image_url: str | None = None,
    image_asset_id: str | None = None,
    hint: str | None = None,
) -> WardrobeItemDraft:
    """识别已经由本地文件卷读取的图片字节。"""

    if recognizer is None:
        raise WardrobeVisionUnavailableError(
            "当前部署未启用衣物照片识别，请手动录入衣橱单品。",
        )

    validate_wardrobe_image(image=image, max_bytes=max_image_bytes)
    with observe_operation(
        logger,
        "service.wardrobe_image_recognition",
        user=anonymize_identifier(user_id),
        content_type=image.content_type.value,
        image_bytes=len(image.content),
    ) as observation:
        with observe_operation(
            logger,
            "provider.wardrobe_vision",
            provider_type=type(recognizer).__name__,
        ):
            recognition = await recognizer.recognize(image, hint)

        draft = build_wardrobe_item_draft(
            draft_id=str(uuid4()),
            recognition=recognition,
            image_url=image_url,
            image_asset_id=image_asset_id,
            min_confidence=min_confidence,
        )
        observation.add_fields(
            confidence=draft.confidence,
            uncertain_field_count=len(draft.uncertain_fields),
            missing_field_count=len(draft.missing_fields),
        )
    return draft


async def recognize_wardrobe_image_content_many(
    *,
    recognizer: WardrobeImageRecognizer | None,
    user_id: str,
    image: WardrobeImage,
    max_image_bytes: int,
    min_confidence: float,
    max_detected_items: int = 8,
    image_url: str | None = None,
    image_asset_id: str | None = None,
    hint: str | None = None,
) -> tuple[WardrobeItemDraft, ...]:
    """识别一张照片中的多件衣物，并为每件生成独立草稿。"""

    if recognizer is None:
        raise WardrobeVisionUnavailableError(
            "当前部署未启用衣物照片识别，请手动录入衣橱单品。",
        )

    validate_wardrobe_image(image=image, max_bytes=max_image_bytes)
    with observe_operation(
        logger,
        "service.wardrobe_image_recognition_many",
        user=anonymize_identifier(user_id),
        content_type=image.content_type.value,
        image_bytes=len(image.content),
    ) as observation:
        with observe_operation(
            logger,
            "provider.wardrobe_vision_many",
            provider_type=type(recognizer).__name__,
        ):
            recognize_many = getattr(recognizer, "recognize_many", None)
            if callable(recognize_many):
                recognitions = await recognize_many(image, hint)
            else:
                recognitions = (await recognizer.recognize(image, hint),)

        if not recognitions:
            raise WardrobeVisionProviderError(
                "衣物照片识别服务没有返回任何衣物结果。",
            )
        if len(recognitions) > max_detected_items:
            raise WardrobeVisionProviderError(
                "衣物照片识别结果超过单张照片允许的衣物数量。",
            )

        drafts = tuple(
            build_wardrobe_item_draft(
                draft_id=str(uuid4()),
                recognition=recognition,
                image_url=image_url,
                image_asset_id=image_asset_id,
                min_confidence=min_confidence,
            )
            for recognition in recognitions
        )
        observation.add_fields(
            draft_count=len(drafts),
            uncertain_field_count=sum(
                len(draft.uncertain_fields) for draft in drafts
            ),
            missing_field_count=sum(len(draft.missing_fields) for draft in drafts),
        )

    return drafts
