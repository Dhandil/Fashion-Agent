"""把视觉模型识别结果转换成待确认草稿的确定性规则。"""

from collections.abc import Sequence

from app.domain.entities.wardrobe_draft import (
    WardrobeItemDraft,
    WardrobeItemRecognition,
)

# 草稿中允许出现的字段顺序，确保输出的字段列表稳定可比较
DRAFT_FIELD_ORDER: tuple[str, ...] = (
    "name",
    "category",
    "colors",
    "materials",
    "style_tags",
    "seasons",
    "scenarios",
)

# 创建衣橱单品必须具备、照片识别不到时只能由用户补充的字段
_REQUIRED_FIELDS: tuple[str, ...] = (
    "name",
    "category",
)

# 品牌和尺码无法从一张照片可靠判断，因此不接受模型给出的猜测
UNRECOGNIZABLE_FIELDS: tuple[str, ...] = (
    "brand",
    "size",
)

# 单个序列字段最多保留的条目数，避免模型输出过长标签污染衣橱
_MAX_SEQUENCE_ITEMS = 5

# 序列条目、名称、品类和补充说明的字符上限，与衣橱实体保持一致
_MAX_SEQUENCE_ITEM_CHARS = 100
_MAX_NAME_CHARS = 200
_MAX_CATEGORY_CHARS = 100
_MAX_NOTES_CHARS = 1000


def build_wardrobe_item_draft(
    *,
    draft_id: str,
    recognition: WardrobeItemRecognition,
    image_url: str | None = None,
    image_asset_id: str | None = None,
    min_confidence: float,
) -> WardrobeItemDraft:
    """净化识别结果，并明确标记需要用户确认和补充的字段。"""

    name = _normalized_text(
        recognition.name,
        max_chars=_MAX_NAME_CHARS,
    )
    category = _normalized_text(
        recognition.category,
        max_chars=_MAX_CATEGORY_CHARS,
    )
    sequences = {
        "colors": _normalized_unique(recognition.colors),
        "materials": _normalized_unique(recognition.materials),
        "style_tags": _normalized_unique(recognition.style_tags),
        "seasons": _normalized_unique(recognition.seasons),
        "scenarios": _normalized_unique(recognition.scenarios),
    }

    recognized_values: dict[str, object] = {
        "name": name,
        "category": category,
        **sequences,
    }

    # 必填字段缺失时如实标记，不使用模型猜测填满草稿
    missing_fields = tuple(
        field_name
        for field_name in _REQUIRED_FIELDS
        if not recognized_values[field_name]
    )
    uncertain_fields = _resolve_uncertain_fields(
        reported_fields=recognition.uncertain_fields,
        recognized_values=recognized_values,
        missing_fields=missing_fields,
        confidence=recognition.confidence,
        min_confidence=min_confidence,
    )

    return WardrobeItemDraft(
        draft_id=draft_id,
        name=name,
        category=category,
        colors=sequences["colors"],
        materials=sequences["materials"],
        style_tags=sequences["style_tags"],
        seasons=sequences["seasons"],
        scenarios=sequences["scenarios"],
        notes=_normalized_text(
            recognition.notes,
            max_chars=_MAX_NOTES_CHARS,
        ),
        image_url=image_url,
        image_asset_id=image_asset_id,
        confidence=recognition.confidence,
        uncertain_fields=uncertain_fields,
        missing_fields=missing_fields,
        unrecognizable_fields=UNRECOGNIZABLE_FIELDS,
    )


def _resolve_uncertain_fields(
    *,
    reported_fields: Sequence[str],
    recognized_values: dict[str, object],
    missing_fields: tuple[str, ...],
    confidence: float,
    min_confidence: float,
) -> tuple[str, ...]:
    """整体置信度不足时，把全部已识别字段都交给用户确认。"""

    if confidence < min_confidence:
        uncertain_keys = set(DRAFT_FIELD_ORDER)
    else:
        # 只接受模型给出的已知字段名，忽略无法对应到草稿的内容
        uncertain_keys = {
            field_name.strip().casefold() for field_name in reported_fields
        } & set(DRAFT_FIELD_ORDER)

    # 待确认字段必须已经识别出内容；没有识别到内容的必填字段属于缺失
    return tuple(
        field_name
        for field_name in DRAFT_FIELD_ORDER
        if field_name in uncertain_keys
        and field_name not in missing_fields
        and recognized_values[field_name]
    )


def _normalized_text(
    value: str | None,
    *,
    max_chars: int,
) -> str | None:
    """去除首尾空格并截断超长文本，空文本视为未识别。"""

    if value is None:
        return None

    normalized = value.strip()
    if not normalized:
        return None

    return normalized[:max_chars]


def _normalized_unique(
    values: Sequence[str],
) -> tuple[str, ...]:
    """保留原始顺序，按大小写去重、截断并限制条目数量。"""

    result: list[str] = []
    seen: set[str] = set()

    for value in values:
        normalized = value.strip()[:_MAX_SEQUENCE_ITEM_CHARS]
        key = normalized.casefold()
        if not normalized or key in seen:
            continue

        seen.add(key)
        result.append(normalized)

        if len(result) >= _MAX_SEQUENCE_ITEMS:
            break

    return tuple(result)
