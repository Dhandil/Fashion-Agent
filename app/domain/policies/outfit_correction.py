"""不依赖模型的高置信度 Outfit 局部修复。"""

from collections.abc import Mapping, Sequence
from typing import Any

from app.domain.entities.outfit import (
    OutfitItem,
    OutfitItemSource,
    OutfitRecommendation,
)
from app.domain.policies.wardrobe_candidates import (
    WardrobeCandidateExclusionReason,
    WardrobeCandidateSelection,
)


def _record_id(
    record: Mapping[str, Any],
) -> str | None:
    """读取合法衣橱 ID。"""

    value = record.get("wardrobe_item_id")
    return value if isinstance(value, str) and value else None


def repair_hot_weather_wardrobe_items(
    recommendation: OutfitRecommendation,
    *,
    wardrobe_records: Sequence[Mapping[str, Any]],
    selection: WardrobeCandidateSelection,
) -> OutfitRecommendation | None:
    """用同品类真实候选替换被高温规则排除的衣橱单品。"""

    hot_conflict_ids = {
        exclusion.wardrobe_item_id
        for exclusion in selection.exclusions
        if exclusion.reason
        is WardrobeCandidateExclusionReason.HOT_WEATHER_CONFLICT
        and exclusion.wardrobe_item_id is not None
    }
    if not hot_conflict_ids:
        return None

    records_by_id = {
        record_id: record
        for record in wardrobe_records
        if (record_id := _record_id(record)) is not None
    }
    used_ids = {
        item.source_reference_id
        for item in recommendation.items
        if item.source is OutfitItemSource.WARDROBE
        and item.source_reference_id not in hot_conflict_ids
    }
    eligible_by_category: dict[str, list[Mapping[str, Any]]] = {}
    for record in selection.eligible_records:
        category = record.get("category")
        record_id = _record_id(record)
        name = record.get("name")
        if (
            not isinstance(category, str)
            or not category
            or record_id is None
            or not isinstance(name, str)
            or not name
        ):
            continue
        eligible_by_category.setdefault(
            category,
            [],
        ).append(record)

    repaired_items: list[OutfitItem] = []
    replaced_count = 0
    for item in recommendation.items:
        if (
            item.source is not OutfitItemSource.WARDROBE
            or item.source_reference_id not in hot_conflict_ids
        ):
            repaired_items.append(item)
            continue

        original_record = records_by_id.get(
            item.source_reference_id or "",
        )
        category = (
            original_record.get("category")
            if original_record is not None
            else None
        )
        if not isinstance(category, str):
            return None
        replacement = next(
            (
                candidate
                for candidate in eligible_by_category.get(
                    category,
                    [],
                )
                if _record_id(candidate) not in used_ids
            ),
            None,
        )
        if replacement is None:
            return None

        replacement_id = _record_id(replacement)
        replacement_name = replacement.get("name")
        if replacement_id is None or not isinstance(
            replacement_name,
            str,
        ):
            return None
        used_ids.add(replacement_id)
        repaired_items.append(
            item.model_copy(
                update={
                    "name": replacement_name,
                    "source_reference_id": replacement_id,
                    "reason": (
                        "高温下改用当前可用的轻薄同类单品。"
                    ),
                },
            ),
        )
        replaced_count += 1

    if replaced_count == 0:
        return None

    repaired_alternatives = tuple(
        item
        for item in recommendation.alternatives
        if not (
            item.source is OutfitItemSource.WARDROBE
            and item.source_reference_id in hot_conflict_ids
        )
    )
    return recommendation.model_copy(
        update={
            "items": tuple(repaired_items),
            "alternatives": repaired_alternatives,
        },
    )
