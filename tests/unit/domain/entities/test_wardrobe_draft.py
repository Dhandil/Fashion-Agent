"""衣物照片识别结果与草稿领域实体测试。"""

import pytest
from pydantic import ValidationError

from app.domain.entities.wardrobe_draft import (
    WardrobeItemDraft,
    WardrobeItemRecognition,
)


def test_recognition_ignores_identity_fields() -> None:
    """验证模型多输出的身份和状态字段不会进入领域对象。"""

    recognition = WardrobeItemRecognition.model_validate(
        {
            "name": "浅蓝色亚麻衬衫",
            "category": "衬衫",
            "confidence": 0.8,
            "user_id": "user-999",
            "wardrobe_item_id": "wardrobe-999",
            "status": "available",
        },
    )

    assert recognition.name == "浅蓝色亚麻衬衫"
    assert not hasattr(
        recognition,
        "user_id",
    )
    assert not hasattr(
        recognition,
        "status",
    )


def test_recognition_rejects_out_of_range_confidence() -> None:
    """验证置信度必须落在 0 到 1 之间。"""

    with pytest.raises(ValidationError):
        WardrobeItemRecognition(
            confidence=1.5,
        )


def test_draft_requires_confirmation_flag() -> None:
    """验证草稿不能被构造成无需确认的事实。"""

    with pytest.raises(ValidationError):
        WardrobeItemDraft(
            draft_id="draft-001",
            name="浅蓝色亚麻衬衫",
            category="衬衫",
            requires_confirmation=False,
        )


def test_draft_missing_fields_must_match_empty_values() -> None:
    """验证空的必填字段必须同时出现在 missing_fields。"""

    with pytest.raises(ValidationError):
        WardrobeItemDraft(
            draft_id="draft-001",
            name=None,
            category="衬衫",
            missing_fields=(),
        )


def test_draft_rejects_field_in_both_lists() -> None:
    """验证同一字段不能既待确认又完全缺失。"""

    with pytest.raises(ValidationError):
        WardrobeItemDraft(
            draft_id="draft-001",
            name=None,
            category=None,
            uncertain_fields=(
                "name",
            ),
            missing_fields=(
                "name",
                "category",
            ),
        )


def test_draft_is_frozen() -> None:
    """验证草稿创建后不能被原地修改。"""

    draft = WardrobeItemDraft(
        draft_id="draft-001",
        name="浅蓝色亚麻衬衫",
        category="衬衫",
    )

    with pytest.raises(ValidationError):
        draft.name = "其他衣物"  # type: ignore[misc]
