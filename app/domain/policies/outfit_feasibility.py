"""不依赖 LLM 的 Outfit 可执行性规则。"""

from collections.abc import Mapping, Sequence
from typing import Any

from app.agents.schemas.requirements import (
    OutfitRequirementAnalysis,
    RequestIntent,
)
from app.domain.entities.outfit import (
    OutfitItem,
    OutfitItemSource,
    OutfitRecommendation,
)
from app.domain.entities.outfit_validation import (
    OutfitFeasibilityIssue,
    OutfitFeasibilityReport,
    OutfitIssueCode,
    OutfitIssueSeverity,
)
from app.domain.entities.weather import WeatherContext
from app.domain.policies.style_constraints import (
    EffectiveStyleConstraints,
)
from app.domain.policies.wardrobe_candidates import (
    HOT_WEATHER_INCOMPATIBLE_TERMS,
)

_UPPER_ROLE_TERMS = (
    "上装",
    "上衣",
    "衬衫",
    "内搭",
    "针织衫",
)
_LOWER_ROLE_TERMS = (
    "下装",
    "裤",
    "半身裙",
)
_ONE_PIECE_ROLE_TERMS = (
    "连衣裙",
    "连体",
)
_FOOTWEAR_ROLE_TERMS = (
    "鞋",
    "鞋履",
)
_OUTERWEAR_ROLE_TERMS = (
    "外套",
    "大衣",
    "夹克",
    "风衣",
)
_WARMING_TERMS = (
    "外套",
    "大衣",
    "羽绒",
    "毛衣",
    "保暖",
    "叠穿",
    "加绒",
)
_RAIN_PROTECTION_TERMS = (
    "雨伞",
    "雨具",
    "防水",
    "防滑",
    "雨鞋",
)


def _record_by_id(
    records: Sequence[Mapping[str, Any]],
    id_field: str,
) -> dict[str, Mapping[str, Any]]:
    """把工具记录转换为只包含合法字符串 ID 的索引。"""

    return {
        record_id: record
        for record in records
        if isinstance(
            record_id := record.get(id_field),
            str,
        )
        and record_id
    }


def _contains_role(
    items: Sequence[OutfitItem],
    terms: tuple[str, ...],
) -> bool:
    """按稳定中文角色词识别 Outfit 的组成部分。"""

    return any(any(term in item.role for term in terms) for item in items)


def _check_source_evidence(
    recommendation: OutfitRecommendation,
    wardrobe_records: Sequence[Mapping[str, Any]],
    product_records: Sequence[Mapping[str, Any]],
) -> list[OutfitFeasibilityIssue]:
    """检查衣橱和商品来源是否真实、可用且没有重复。"""

    issues: list[OutfitFeasibilityIssue] = []
    wardrobe_by_id = _record_by_id(
        wardrobe_records,
        "wardrobe_item_id",
    )
    product_by_id = _record_by_id(
        product_records,
        "product_id",
    )
    seen_references: set[tuple[OutfitItemSource, str]] = set()

    for item in (
        *recommendation.items,
        *recommendation.alternatives,
    ):
        reference_id = item.source_reference_id
        if reference_id is None:
            continue

        reference_key = (
            item.source,
            reference_id,
        )
        if reference_key in seen_references:
            issues.append(
                OutfitFeasibilityIssue(
                    code=(OutfitIssueCode.DUPLICATE_SOURCE_ITEM),
                    severity=OutfitIssueSeverity.ERROR,
                    message="同一真实单品不能在一套方案中重复引用。",
                    item_reference_id=reference_id,
                ),
            )
        seen_references.add(reference_key)

        if item.source is OutfitItemSource.WARDROBE:
            record = wardrobe_by_id.get(reference_id)
            if record is None:
                issues.append(
                    OutfitFeasibilityIssue(
                        code=(OutfitIssueCode.UNKNOWN_SOURCE_ID),
                        severity=OutfitIssueSeverity.ERROR,
                        message="衣橱单品不在当前轮真实查询结果中。",
                        item_reference_id=reference_id,
                    ),
                )
            elif record.get("status") != "available":
                issues.append(
                    OutfitFeasibilityIssue(
                        code=(OutfitIssueCode.UNAVAILABLE_WARDROBE_ITEM),
                        severity=OutfitIssueSeverity.ERROR,
                        message="衣橱单品当前不可参与穿搭。",
                        item_reference_id=reference_id,
                    ),
                )

        if item.source is OutfitItemSource.PRODUCT:
            record = product_by_id.get(reference_id)
            if record is None:
                issues.append(
                    OutfitFeasibilityIssue(
                        code=(OutfitIssueCode.UNKNOWN_SOURCE_ID),
                        severity=OutfitIssueSeverity.ERROR,
                        message="商品不在当前轮真实查询结果中。",
                        item_reference_id=reference_id,
                    ),
                )
            elif record.get("in_stock") is False:
                issues.append(
                    OutfitFeasibilityIssue(
                        code=(OutfitIssueCode.OUT_OF_STOCK_PRODUCT),
                        severity=OutfitIssueSeverity.ERROR,
                        message="商品当前无库存，不能作为可执行单品。",
                        item_reference_id=reference_id,
                    ),
                )

    return issues


def _check_core_roles(
    recommendation: OutfitRecommendation,
    analysis: OutfitRequirementAnalysis | None,
) -> list[OutfitFeasibilityIssue]:
    """完整穿搭请求必须覆盖身体核心角色和鞋履。"""

    if analysis is None or analysis.intent not in {
        RequestIntent.OUTFIT,
        RequestIntent.OUTFIT_ADJUSTMENT,
    }:
        return []

    items = recommendation.items
    has_upper = _contains_role(items, _UPPER_ROLE_TERMS)
    has_lower = _contains_role(items, _LOWER_ROLE_TERMS)
    has_one_piece = _contains_role(
        items,
        _ONE_PIECE_ROLE_TERMS,
    )
    has_footwear = _contains_role(
        items,
        _FOOTWEAR_ROLE_TERMS,
    )
    missing_roles: list[str] = []

    if not has_one_piece:
        if not has_upper:
            missing_roles.append("上装")
        if not has_lower:
            missing_roles.append("下装")
    if not has_footwear:
        missing_roles.append("鞋履")

    if not missing_roles:
        return []
    return [
        OutfitFeasibilityIssue(
            code=OutfitIssueCode.MISSING_CORE_ROLE,
            severity=OutfitIssueSeverity.ERROR,
            message=("完整穿搭缺少核心角色：" + "、".join(missing_roles)),
        ),
    ]


def _record_values(
    record: Mapping[str, Any] | None,
    field_name: str,
) -> tuple[str, ...]:
    """从真实工具记录中读取结构化偏好字段。"""

    if record is None:
        return ()
    value = record.get(field_name)
    if isinstance(value, str):
        return (value.casefold(),)
    if isinstance(value, Sequence):
        return tuple(item.casefold() for item in value if isinstance(item, str))
    return ()


def _contains_avoided_value(
    values: Sequence[str],
    avoided_values: Sequence[str],
) -> bool:
    """判断结构化值或单品名称是否包含当前轮明确避免项。"""

    normalized_avoidances = tuple(
        value.strip().casefold() for value in avoided_values if value.strip()
    )
    return any(
        avoided in value or value in avoided
        for value in values
        for avoided in normalized_avoidances
    )


def _check_explicit_avoidances(
    recommendation: OutfitRecommendation,
    wardrobe_records: Sequence[Mapping[str, Any]],
    product_records: Sequence[Mapping[str, Any]],
    analysis: OutfitRequirementAnalysis | None,
    style_constraints: EffectiveStyleConstraints | None,
) -> list[OutfitFeasibilityIssue]:
    """阻止当前有效约束中避免的颜色、材质或风格进入方案。"""

    if style_constraints is not None:
        avoided_materials = style_constraints.avoided_materials
        avoided_colors = style_constraints.avoided_colors
        avoided_styles = style_constraints.avoided_styles
    elif analysis is not None:
        avoided_materials = analysis.avoided_materials
        avoided_colors = analysis.avoided_colors
        avoided_styles = analysis.avoided_styles
    else:
        return []
    wardrobe_by_id = _record_by_id(
        wardrobe_records,
        "wardrobe_item_id",
    )
    product_by_id = _record_by_id(
        product_records,
        "product_id",
    )
    issues: list[OutfitFeasibilityIssue] = []

    for item in (
        *recommendation.items,
        *recommendation.alternatives,
    ):
        record: Mapping[str, Any] | None = None
        if item.source is OutfitItemSource.WARDROBE:
            record = wardrobe_by_id.get(
                item.source_reference_id or "",
            )
        elif item.source is OutfitItemSource.PRODUCT:
            record = product_by_id.get(
                item.source_reference_id or "",
            )

        item_name = (item.name.casefold(),)
        checks = (
            (
                OutfitIssueCode.AVOIDED_MATERIAL,
                "materials",
                avoided_materials,
                "方案使用了当前有效约束中避免的材质。",
            ),
            (
                OutfitIssueCode.AVOIDED_COLOR,
                "colors",
                avoided_colors,
                "方案使用了当前有效约束中避免的颜色。",
            ),
            (
                OutfitIssueCode.AVOIDED_STYLE,
                "style_tags",
                avoided_styles,
                "方案使用了当前有效约束中避免的风格。",
            ),
        )
        for code, field_name, avoided_values, message in checks:
            values = (
                *_record_values(record, field_name),
                *item_name,
            )
            if _contains_avoided_value(
                values,
                avoided_values,
            ):
                issues.append(
                    OutfitFeasibilityIssue(
                        code=code,
                        severity=OutfitIssueSeverity.ERROR,
                        message=message,
                        item_reference_id=(item.source_reference_id),
                    ),
                )

    return issues


def _check_scenario(
    recommendation: OutfitRecommendation,
    analysis: OutfitRequirementAnalysis | None,
) -> list[OutfitFeasibilityIssue]:
    """当前请求明确场景时，推荐场景必须能够对应。"""

    if analysis is None or not analysis.scenario:
        return []
    expected = analysis.scenario.strip().casefold()
    actual = recommendation.scenario.strip().casefold()
    if expected in actual or actual in expected:
        return []
    return [
        OutfitFeasibilityIssue(
            code=OutfitIssueCode.SCENARIO_MISMATCH,
            severity=OutfitIssueSeverity.ERROR,
            message="推荐场景与当前用户明确场景不一致。",
        ),
    ]


def _check_weather(
    recommendation: OutfitRecommendation,
    weather: WeatherContext | None,
    wardrobe_records: Sequence[Mapping[str, Any]],
    product_records: Sequence[Mapping[str, Any]],
) -> list[OutfitFeasibilityIssue]:
    """使用推荐文本和真实来源记录识别高置信度天气冲突。"""

    if weather is None:
        return []

    issues: list[OutfitFeasibilityIssue] = []
    wardrobe_by_id = _record_by_id(
        wardrobe_records,
        "wardrobe_item_id",
    )
    product_by_id = _record_by_id(
        product_records,
        "product_id",
    )
    # 天气适配只检查实际选中的单品及其真实来源记录。
    # 推荐理由可能描述“已替换厚羊毛”等历史信息，不能当成当前穿着事实。
    outfit_text_parts: list[str] = []
    for item in (
        *recommendation.items,
        *recommendation.alternatives,
    ):
        outfit_text_parts.append(item.name)
        record: Mapping[str, Any] | None = None
        if item.source is OutfitItemSource.WARDROBE:
            record = wardrobe_by_id.get(
                item.source_reference_id or "",
            )
        elif item.source is OutfitItemSource.PRODUCT:
            record = product_by_id.get(
                item.source_reference_id or "",
            )
        if record is not None:
            for field_name in (
                "name",
                "category",
                "materials",
                "style_tags",
                "notes",
            ):
                value = record.get(field_name)
                if isinstance(value, str):
                    outfit_text_parts.append(value)
                elif isinstance(value, Sequence):
                    outfit_text_parts.extend(
                        entry
                        for entry in value
                        if isinstance(entry, str)
                    )
    outfit_text = " ".join(
        part for part in outfit_text_parts if part
    )
    high_temperature = max(
        value
        for value in (
            weather.temperature_max_c,
            weather.feels_like_c,
            -101,
        )
        if value is not None
    )
    low_temperature_candidates = [
        value
        for value in (
            weather.temperature_min_c,
            weather.feels_like_c,
        )
        if value is not None
    ]
    low_temperature = min(low_temperature_candidates) if low_temperature_candidates else None

    if high_temperature >= 30 and any(
        term in outfit_text
        for term in HOT_WEATHER_INCOMPATIBLE_TERMS
    ):
        issues.append(
            OutfitFeasibilityIssue(
                code=(OutfitIssueCode.HOT_WEATHER_CONFLICT),
                severity=OutfitIssueSeverity.ERROR,
                message="高温天气下不应使用明显厚重保暖单品。",
            ),
        )

    if (
        low_temperature is not None
        and low_temperature <= 10
        and not _contains_role(
            recommendation.items,
            _OUTERWEAR_ROLE_TERMS,
        )
        and not any(term in outfit_text for term in _WARMING_TERMS)
    ):
        issues.append(
            OutfitFeasibilityIssue(
                code=OutfitIssueCode.COLD_WEATHER_RISK,
                severity=OutfitIssueSeverity.WARNING,
                message="低温天气下方案没有明确的保暖层。",
            ),
        )

    has_precipitation_risk = (
        weather.precipitation_probability is not None and weather.precipitation_probability >= 60
    ) or (weather.condition is not None and any(term in weather.condition for term in ("雨", "雪")))
    if has_precipitation_risk and not any(term in outfit_text for term in _RAIN_PROTECTION_TERMS):
        issues.append(
            OutfitFeasibilityIssue(
                code=OutfitIssueCode.PRECIPITATION_RISK,
                severity=OutfitIssueSeverity.WARNING,
                message="存在明显降水风险，但方案没有说明雨具或防滑防水措施。",
            ),
        )

    return issues


def evaluate_outfit_feasibility(
    recommendation: OutfitRecommendation,
    *,
    wardrobe_records: Sequence[Mapping[str, Any]] = (),
    product_records: Sequence[Mapping[str, Any]] = (),
    weather: WeatherContext | None = None,
    requirement_analysis: (OutfitRequirementAnalysis | None) = None,
    style_constraints: EffectiveStyleConstraints | None = None,
) -> OutfitFeasibilityReport:
    """汇总来源、完整性、场景和天气规则并生成稳定报告。"""

    issues = (
        *_check_source_evidence(
            recommendation,
            wardrobe_records,
            product_records,
        ),
        *_check_explicit_avoidances(
            recommendation,
            wardrobe_records,
            product_records,
            requirement_analysis,
            style_constraints,
        ),
        *_check_core_roles(
            recommendation,
            requirement_analysis,
        ),
        *_check_scenario(
            recommendation,
            requirement_analysis,
        ),
        *_check_weather(
            recommendation,
            weather,
            wardrobe_records,
            product_records,
        ),
    )
    return OutfitFeasibilityReport(
        is_executable=not any(issue.severity is OutfitIssueSeverity.ERROR for issue in issues),
        issues=issues,
    )
