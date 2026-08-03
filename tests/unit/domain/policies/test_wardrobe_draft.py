"""识别结果转换为待确认草稿的规则测试。"""

from app.domain.entities.wardrobe_draft import (
    WardrobeItemRecognition,
)
from app.domain.policies.wardrobe_draft import (
    UNRECOGNIZABLE_FIELDS,
    build_wardrobe_item_draft,
)


def test_draft_normalizes_sequences() -> None:
    """验证序列字段去空格、去重、限制数量并保留原始顺序。"""

    recognition = WardrobeItemRecognition(
        name="  浅蓝色亚麻衬衫  ",
        category=" 衬衫 ",
        colors=(
            " 浅蓝色 ",
            "浅蓝色",
            "白色",
            "",
        ),
        style_tags=(
            "简约",
            "通勤",
            "文艺",
            "复古",
            "度假",
            "街头",
        ),
        confidence=0.9,
    )

    draft = build_wardrobe_item_draft(
        draft_id="draft-001",
        recognition=recognition,
        min_confidence=0.5,
    )

    assert draft.name == "浅蓝色亚麻衬衫"
    assert draft.category == "衬衫"
    assert draft.colors == (
        "浅蓝色",
        "白色",
    )
    # 单个序列最多保留 5 项，避免模型标签污染衣橱
    assert len(draft.style_tags) == 5
    assert draft.requires_confirmation is True


def test_draft_reports_missing_required_fields() -> None:
    """验证识别不到名称和品类时如实标记，不虚构内容。"""

    recognition = WardrobeItemRecognition(
        name="   ",
        category=None,
        colors=(
            "黑色",
        ),
        confidence=0.9,
    )

    draft = build_wardrobe_item_draft(
        draft_id="draft-001",
        recognition=recognition,
        min_confidence=0.5,
    )

    assert draft.name is None
    assert draft.category is None
    assert draft.missing_fields == (
        "name",
        "category",
    )


def test_draft_marks_all_recognized_fields_when_confidence_is_low() -> None:
    """验证整体置信度不足时，已识别字段全部交给用户确认。"""

    recognition = WardrobeItemRecognition(
        name="深灰色西裤",
        category="长裤",
        colors=(
            "深灰色",
        ),
        materials=(),
        confidence=0.2,
    )

    draft = build_wardrobe_item_draft(
        draft_id="draft-001",
        recognition=recognition,
        min_confidence=0.5,
    )

    assert draft.uncertain_fields == (
        "name",
        "category",
        "colors",
    )


def test_draft_keeps_reported_uncertain_fields_only() -> None:
    """验证置信度足够时只接受模型给出的已知字段名。"""

    recognition = WardrobeItemRecognition(
        name="米色风衣",
        category="外套",
        materials=(
            "棉",
        ),
        uncertain_fields=(
            "MATERIALS",
            " colors ",
            "brand",
            "价格",
        ),
        confidence=0.8,
    )

    draft = build_wardrobe_item_draft(
        draft_id="draft-001",
        recognition=recognition,
        min_confidence=0.5,
    )

    # colors 虽然被模型标记，但本次没有识别到内容，不作为待确认字段
    assert draft.uncertain_fields == (
        "materials",
    )


def test_draft_never_reports_missing_field_as_uncertain() -> None:
    """验证完全缺失的字段不会同时出现在待确认列表。"""

    recognition = WardrobeItemRecognition(
        name=None,
        category="鞋履",
        uncertain_fields=(
            "name",
            "category",
        ),
        confidence=0.9,
    )

    draft = build_wardrobe_item_draft(
        draft_id="draft-001",
        recognition=recognition,
        min_confidence=0.5,
    )

    assert draft.missing_fields == (
        "name",
    )
    assert draft.uncertain_fields == (
        "category",
    )


def test_draft_always_requires_user_to_provide_brand_and_size() -> None:
    """验证品牌和尺码不接受模型猜测，只能由用户补充。"""

    recognition = WardrobeItemRecognition.model_validate(
        {
            "name": "白色运动鞋",
            "category": "鞋履",
            "brand": "某品牌",
            "size": "42",
            "confidence": 0.9,
        },
    )

    draft = build_wardrobe_item_draft(
        draft_id="draft-001",
        recognition=recognition,
        min_confidence=0.5,
    )

    assert draft.unrecognizable_fields == UNRECOGNIZABLE_FIELDS
    assert "某品牌" not in draft.model_dump_json()


def test_draft_truncates_overlong_text() -> None:
    """验证超长文本按衣橱实体上限截断。"""

    recognition = WardrobeItemRecognition(
        name="长" * 500,
        category="类" * 300,
        notes="说明" * 800,
        confidence=0.9,
    )

    draft = build_wardrobe_item_draft(
        draft_id="draft-001",
        recognition=recognition,
        image_url="https://example.test/item.jpg",
        min_confidence=0.5,
    )

    assert draft.name is not None
    assert len(draft.name) == 200
    assert draft.category is not None
    assert len(draft.category) == 100
    assert draft.notes is not None
    assert len(draft.notes) == 1_000
    assert draft.image_url == "https://example.test/item.jpg"
