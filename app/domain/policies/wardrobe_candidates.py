"""根据当前事实选择可以交给 Outfit 模型的衣橱候选。"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from app.domain.entities.weather import WeatherContext

_HOT_WEATHER_INCOMPATIBLE_TERMS = (
    "羽绒",
    "加绒",
    "厚呢",
    "厚羊毛",
    "羊毛大衣",
    "皮草",
)
_SEARCHABLE_FIELDS = (
    "name",
    "category",
    "materials",
    "style_tags",
    "seasons",
    "notes",
)


class WardrobeCandidateExclusionReason(StrEnum):
    """衣物没有进入当前模型候选集的稳定原因。"""

    UNAVAILABLE = "unavailable"
    HOT_WEATHER_CONFLICT = "hot_weather_conflict"
    AVOIDED_STYLE = "avoided_style"
    AVOIDED_COLOR = "avoided_color"
    AVOIDED_MATERIAL = "avoided_material"


@dataclass(frozen=True, slots=True)
class WardrobeCandidateExclusion:
    """一条不包含用户正文的候选排除记录。"""

    wardrobe_item_id: str | None
    reason: WardrobeCandidateExclusionReason


@dataclass(frozen=True, slots=True)
class WardrobeCandidateSelection:
    """模型可见候选与被确定性排除的原因。"""

    eligible_records: tuple[dict[str, Any], ...]
    exclusions: tuple[WardrobeCandidateExclusion, ...]


def _maximum_known_temperature(
    weather: WeatherContext | None,
) -> float | None:
    """返回最高温度或体感温度中的已知最大值。"""

    if weather is None:
        return None
    temperatures = tuple(
        temperature
        for temperature in (
            weather.temperature_max_c,
            weather.feels_like_c,
        )
        if temperature is not None
    )
    if not temperatures:
        return None
    return max(temperatures)


def _record_searchable_text(
    record: Mapping[str, Any],
) -> str:
    """只拼接与天气适配有关的普通衣物字段。"""

    values: list[str] = []
    for field_name in _SEARCHABLE_FIELDS:
        value = record.get(field_name)
        if isinstance(value, str):
            values.append(value)
        elif isinstance(value, Sequence):
            values.extend(item for item in value if isinstance(item, str))
    return " ".join(values).casefold()


def _record_field_values(
    record: Mapping[str, Any],
    field_name: str,
) -> tuple[str, ...]:
    """读取颜色、材质或风格等结构化字符串列表。"""

    value = record.get(field_name)
    if isinstance(value, str):
        return (value.casefold(),)
    if isinstance(value, Sequence):
        return tuple(item.casefold() for item in value if isinstance(item, str))
    return ()


def _matches_avoidance(
    values: tuple[str, ...],
    avoided_values: Sequence[str],
) -> bool:
    """允许“羊毛”匹配“羊毛混纺”等明确包含关系。"""

    normalized_avoidances = tuple(
        value.strip().casefold() for value in avoided_values if value.strip()
    )
    return any(
        avoided in value or value in avoided
        for value in values
        for avoided in normalized_avoidances
    )


def select_eligible_wardrobe_records(
    records: Sequence[Mapping[str, Any]],
    *,
    weather: WeatherContext | None = None,
    avoided_styles: Sequence[str] = (),
    avoided_colors: Sequence[str] = (),
    avoided_materials: Sequence[str] = (),
) -> WardrobeCandidateSelection:
    """排除不可用或与高温明显冲突的衣物候选。

    `unavailable` 统一代表待洗、清洗中、未干、损坏等当前不能穿的状态，
    这里不再把这些原因拆成更多领域状态。
    """

    effective_temperature = _maximum_known_temperature(
        weather,
    )
    has_high_heat = effective_temperature is not None and effective_temperature >= 30
    eligible_records: list[dict[str, Any]] = []
    exclusions: list[WardrobeCandidateExclusion] = []

    for record in records:
        record_id = record.get("wardrobe_item_id")
        normalized_id = record_id if isinstance(record_id, str) and record_id else None
        if record.get("status") != "available":
            exclusions.append(
                WardrobeCandidateExclusion(
                    wardrobe_item_id=normalized_id,
                    reason=(WardrobeCandidateExclusionReason.UNAVAILABLE),
                ),
            )
            continue

        searchable_text = _record_searchable_text(record)
        if has_high_heat and any(
            term in searchable_text for term in _HOT_WEATHER_INCOMPATIBLE_TERMS
        ):
            exclusions.append(
                WardrobeCandidateExclusion(
                    wardrobe_item_id=normalized_id,
                    reason=(WardrobeCandidateExclusionReason.HOT_WEATHER_CONFLICT),
                ),
            )
            continue

        preference_checks = (
            (
                "materials",
                avoided_materials,
                WardrobeCandidateExclusionReason.AVOIDED_MATERIAL,
            ),
            (
                "colors",
                avoided_colors,
                WardrobeCandidateExclusionReason.AVOIDED_COLOR,
            ),
            (
                "style_tags",
                avoided_styles,
                WardrobeCandidateExclusionReason.AVOIDED_STYLE,
            ),
        )
        preference_exclusion = next(
            (
                reason
                for field_name, avoided_values, reason in preference_checks
                if _matches_avoidance(
                    _record_field_values(record, field_name),
                    avoided_values,
                )
            ),
            None,
        )
        if preference_exclusion is not None:
            exclusions.append(
                WardrobeCandidateExclusion(
                    wardrobe_item_id=normalized_id,
                    reason=preference_exclusion,
                ),
            )
            continue

        eligible_records.append(dict(record))

    return WardrobeCandidateSelection(
        eligible_records=tuple(eligible_records),
        exclusions=tuple(exclusions),
    )
