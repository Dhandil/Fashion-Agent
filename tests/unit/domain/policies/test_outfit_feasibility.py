"""Outfit 可执行性确定性规则测试。"""

from app.agents.schemas.requirements import (
    OutfitRequirementAnalysis,
    RequestIntent,
)
from app.domain.entities.outfit import (
    OutfitItem,
    OutfitRecommendation,
)
from app.domain.entities.outfit_validation import (
    OutfitIssueCode,
    OutfitIssueSeverity,
)
from app.domain.entities.weather import WeatherContext
from app.domain.policies.outfit_feasibility import (
    evaluate_outfit_feasibility,
)


def _complete_outfit(
    *,
    scenario: str = "通勤",
    upper_name: str = "浅蓝色衬衫",
) -> OutfitRecommendation:
    """创建包含上装、下装和鞋履的测试穿搭。"""

    return OutfitRecommendation(
        name="简约通勤",
        scenario=scenario,
        items=(
            OutfitItem(
                role="上装",
                name=upper_name,
                source="wardrobe",
                source_reference_id="upper-001",
            ),
            OutfitItem(
                role="下装",
                name="深色长裤",
                source="wardrobe",
                source_reference_id="lower-001",
            ),
            OutfitItem(
                role="鞋履",
                name="黑色乐福鞋",
                source="wardrobe",
                source_reference_id="shoes-001",
            ),
        ),
        recommendation_reason="适合日常通勤。",
    )


def _wardrobe_records() -> tuple[dict[str, str], ...]:
    """创建与完整穿搭对应的可用衣橱证据。"""

    return tuple(
        {
            "wardrobe_item_id": item_id,
            "status": "available",
        }
        for item_id in (
            "upper-001",
            "lower-001",
            "shoes-001",
        )
    )


def _outfit_analysis(
    scenario: str = "通勤",
) -> OutfitRequirementAnalysis:
    """创建完整穿搭请求的结构化分析。"""

    return OutfitRequirementAnalysis(
        intent=RequestIntent.OUTFIT,
        scenario=scenario,
        needs_wardrobe=True,
    )


def test_complete_outfit_with_real_sources_is_executable() -> None:
    """验证核心角色完整且来源可追溯的方案能够通过。"""

    report = evaluate_outfit_feasibility(
        _complete_outfit(),
        wardrobe_records=_wardrobe_records(),
        requirement_analysis=_outfit_analysis(),
    )

    assert report.is_executable is True
    assert report.issues == ()


def test_unknown_wardrobe_source_blocks_outfit() -> None:
    """验证虚构或过期衣橱 ID 会阻止方案返回。"""

    report = evaluate_outfit_feasibility(
        _complete_outfit(),
        wardrobe_records=(),
        requirement_analysis=_outfit_analysis(),
    )

    assert report.is_executable is False
    assert all(issue.code is OutfitIssueCode.UNKNOWN_SOURCE_ID for issue in report.issues)


def test_missing_core_role_blocks_complete_outfit() -> None:
    """验证完整穿搭不能只有一件上装。"""

    recommendation = OutfitRecommendation(
        name="不完整方案",
        scenario="通勤",
        items=(
            OutfitItem(
                role="上装",
                name="白色衬衫",
                source="recommendation",
            ),
        ),
        recommendation_reason="仅提供了上装。",
    )
    report = evaluate_outfit_feasibility(
        recommendation,
        requirement_analysis=_outfit_analysis(),
    )

    assert report.is_executable is False
    assert report.issues[0].code is (OutfitIssueCode.MISSING_CORE_ROLE)
    assert "下装" in report.issues[0].message
    assert "鞋履" in report.issues[0].message


def test_scenario_mismatch_blocks_outfit() -> None:
    """验证明确面试需求不能返回运动场景方案。"""

    report = evaluate_outfit_feasibility(
        _complete_outfit(scenario="运动"),
        wardrobe_records=_wardrobe_records(),
        requirement_analysis=_outfit_analysis(
            scenario="面试",
        ),
    )

    assert report.is_executable is False
    assert any(issue.code is OutfitIssueCode.SCENARIO_MISMATCH for issue in report.issues)


def test_hot_weather_conflict_blocks_heavy_item() -> None:
    """验证高温天气与明显厚重保暖单品冲突。"""

    report = evaluate_outfit_feasibility(
        _complete_outfit(upper_name="厚重羽绒上衣"),
        wardrobe_records=_wardrobe_records(),
        weather=WeatherContext(
            location="上海",
            target_date="2026-08-01",
            temperature_max_c=35,
            source="user_provided",
        ),
        requirement_analysis=_outfit_analysis(),
    )

    assert report.is_executable is False
    assert any(issue.code is OutfitIssueCode.HOT_WEATHER_CONFLICT for issue in report.issues)


def test_hot_weather_uses_referenced_record_material() -> None:
    """验证模型弱化名称时仍以真实衣橱材质判断高温冲突。"""

    recommendation = _complete_outfit(
        upper_name="保暖上衣",
    )
    report = evaluate_outfit_feasibility(
        recommendation,
        wardrobe_records=(
            {
                "wardrobe_item_id": "upper-001",
                "status": "available",
                "materials": ["厚羊毛"],
            },
            *_wardrobe_records()[1:],
        ),
        weather=WeatherContext(
            location="上海",
            target_date="2026-08-02",
            temperature_max_c=36,
            source="user_provided",
        ),
    )

    assert report.is_executable is False
    assert any(
        issue.code is OutfitIssueCode.HOT_WEATHER_CONFLICT
        for issue in report.issues
    )


def test_hot_weather_ignores_historical_reason_text() -> None:
    """验证旧冲突说明不会被误判为当前方案仍使用厚重单品。"""

    recommendation = _complete_outfit(
        upper_name="浅蓝轻薄棉衬衫",
    ).model_copy(
        update={
            "recommendation_reason": (
                "初稿错误使用了厚羊毛上衣，现已替换。"
            ),
            "notes": "不要再穿厚羊毛单品。",
        },
    )
    report = evaluate_outfit_feasibility(
        recommendation,
        wardrobe_records=_wardrobe_records(),
        weather=WeatherContext(
            location="上海",
            target_date="2026-08-02",
            temperature_max_c=36,
            source="user_provided",
        ),
        requirement_analysis=_outfit_analysis(),
    )

    assert report.is_executable is True
    assert not any(
        issue.code is OutfitIssueCode.HOT_WEATHER_CONFLICT
        for issue in report.issues
    )


def test_weather_warning_does_not_block_otherwise_valid_outfit() -> None:
    """验证降雨防护缺失作为警告返回，不武断否决方案。"""

    report = evaluate_outfit_feasibility(
        _complete_outfit(),
        wardrobe_records=_wardrobe_records(),
        weather=WeatherContext(
            location="上海",
            target_date="2026-08-01",
            condition="阵雨",
            precipitation_probability=80,
            source="user_provided",
        ),
        requirement_analysis=_outfit_analysis(),
    )

    assert report.is_executable is True
    assert report.issues[0].code is (OutfitIssueCode.PRECIPITATION_RISK)
    assert report.issues[0].severity is (OutfitIssueSeverity.WARNING)


def test_current_avoidances_block_structured_wardrobe_item() -> None:
    """验证衣橱结构化字段命中当前避雷项时方案不可执行。"""

    wardrobe_records = (
        {
            "wardrobe_item_id": "upper-001",
            "status": "available",
            "colors": ["黑色"],
            "materials": ["羊毛混纺"],
            "style_tags": ["街头风"],
        },
        {
            "wardrobe_item_id": "lower-001",
            "status": "available",
        },
        {
            "wardrobe_item_id": "shoes-001",
            "status": "available",
        },
    )
    analysis = OutfitRequirementAnalysis(
        intent=RequestIntent.OUTFIT,
        scenario="通勤",
        needs_wardrobe=True,
        avoided_colors=("黑色",),
        avoided_materials=("羊毛",),
        avoided_styles=("街头风",),
    )

    report = evaluate_outfit_feasibility(
        _complete_outfit(),
        wardrobe_records=wardrobe_records,
        requirement_analysis=analysis,
    )

    assert report.is_executable is False
    assert {issue.code for issue in report.issues} >= {
        OutfitIssueCode.AVOIDED_COLOR,
        OutfitIssueCode.AVOIDED_MATERIAL,
        OutfitIssueCode.AVOIDED_STYLE,
    }


def test_current_avoidance_checks_recommended_item_name() -> None:
    """验证无结构化来源的建议单品也会按名称检查明确避雷项。"""

    recommendation = OutfitRecommendation(
        name="通勤鞋建议",
        scenario="通勤",
        items=(
            OutfitItem(
                role="鞋履",
                name="黑色乐福鞋",
                source="recommendation",
            ),
        ),
        recommendation_reason="补充一双通勤鞋。",
    )
    analysis = OutfitRequirementAnalysis(
        intent=RequestIntent.OUTFIT_ADJUSTMENT,
        scenario="通勤",
        avoided_colors=("黑色",),
    )

    report = evaluate_outfit_feasibility(
        recommendation,
        requirement_analysis=analysis,
    )

    assert report.is_executable is False
    assert any(issue.code is OutfitIssueCode.AVOIDED_COLOR for issue in report.issues)
