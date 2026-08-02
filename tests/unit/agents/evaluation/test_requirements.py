"""结构化需求分析评测测试。"""

from pathlib import Path

from app.agents.evaluation.requirements import (
    RequirementEvaluationCase,
    RequirementEvaluationExpectation,
    RequirementEvaluationMessage,
    RequirementEvaluationSuite,
    evaluate_requirement_case,
    evaluate_requirement_suite,
    load_requirement_evaluation_suite,
    render_requirement_baseline,
)
from app.agents.schemas.requirements import (
    OutfitRequirementAnalysis,
    RequestIntent,
    RequirementField,
    ShoppingIntent,
)


def _case(
    *,
    case_id: str,
    category: str = "knowledge",
) -> RequirementEvaluationCase:
    """创建最小评测案例。"""

    return RequirementEvaluationCase.model_validate(
        {
            "case_id": case_id,
            "category": category,
            "messages": [
                {"role": "user", "content": "测试请求"},
            ],
            "expected": {
                "intent": "knowledge",
                "is_sufficient": True,
                "needs_wardrobe": False,
                "needs_weather": False,
                "shopping_intent": "none",
            },
        },
    )


def test_committed_suite_covers_requirement_boundaries() -> None:
    """验证可提交案例集覆盖路由、权限和当前偏好边界。"""

    suite = load_requirement_evaluation_suite(
        Path("evaluation/agents/requirement_cases.json"),
    )

    assert suite.schema_version == "1.0"
    assert len(suite.cases) == 18
    assert {case.category for case in suite.cases} == {
        "knowledge",
        "incomplete",
        "wardrobe",
        "adjustment",
        "shopping",
        "shopping_boundary",
        "weather_boundary",
        "preference_boundary",
    }
    positive_and_avoidance = next(
        case
        for case in suite.cases
        if case.case_id == (
            "preference-current-positive-and-avoidance"
        )
    )
    assert positive_and_avoidance.expected.color_preferences == (
        "黑色",
    )
    assert positive_and_avoidance.expected.avoided_colors == (
        "米白色",
    )


def test_evaluate_case_reports_each_mismatched_field() -> None:
    """验证字段偏差和缺失追问字段都会进入结果。"""

    case = RequirementEvaluationCase(
        case_id="incomplete",
        category="incomplete",
        messages=(
            RequirementEvaluationMessage(
                role="user",
                content="帮我搭配",
            ),
        ),
        expected=RequirementEvaluationExpectation(
            intent=RequestIntent.OUTFIT,
            is_sufficient=False,
            needs_wardrobe=False,
            needs_weather=False,
            shopping_intent=ShoppingIntent.NONE,
            missing_fields_contains=(RequirementField.SCENARIO,),
        ),
    )
    actual = OutfitRequirementAnalysis(
        intent=RequestIntent.OTHER,
    )

    result = evaluate_requirement_case(case, actual)

    assert result.passed is False
    assert result.mismatched_fields == (
        "intent",
        "is_sufficient",
        "missing_fields_contains",
    )


def test_omitted_preference_expectation_is_not_compared() -> None:
    """验证未声明的偏好字段代表本案例不关心，而不是必须为空。"""

    case = _case(case_id="partial-expectation")
    actual = OutfitRequirementAnalysis(
        intent=RequestIntent.KNOWLEDGE,
        style_preferences=("简洁",),
        color_preferences=("浅蓝色",),
    )

    result = evaluate_requirement_case(case, actual)

    assert result.passed is True


def test_explicit_empty_preference_expectation_is_compared() -> None:
    """验证显式空列表仍可用于检查模型是否无端增加偏好。"""

    case = _case(case_id="strict-empty-preference").model_copy(
        update={
            "expected": _case(
                case_id="strict-empty-preference",
            ).expected.model_copy(
                update={"style_preferences": ()},
            ),
        },
    )
    actual = OutfitRequirementAnalysis(
        intent=RequestIntent.KNOWLEDGE,
        style_preferences=("简洁",),
    )

    result = evaluate_requirement_case(case, actual)

    assert result.passed is False
    assert result.mismatched_fields == (
        "style_preferences",
    )


def test_evaluate_suite_aggregates_category_rates() -> None:
    """验证总通过率和分类通过率可以独立定位问题。"""

    suite = RequirementEvaluationSuite(
        schema_version="1.0",
        cases=(
            _case(case_id="knowledge-ok"),
            _case(
                case_id="shopping-fail",
                category="shopping",
            ),
        ),
    )
    results_by_id = {
        "knowledge-ok": OutfitRequirementAnalysis(
            intent=RequestIntent.KNOWLEDGE,
        ),
        "shopping-fail": OutfitRequirementAnalysis(
            intent=RequestIntent.SHOPPING,
            shopping_intent=ShoppingIntent.EXPLICIT,
        ),
    }

    report = evaluate_requirement_suite(
        suite,
        lambda case: results_by_id[case.case_id],
    )

    assert report.total_count == 2
    assert report.passed_count == 1
    assert report.pass_rate == 0.5
    assert {result.category: result.pass_rate for result in report.category_results} == {
        "knowledge": 1.0,
        "shopping": 0.0,
    }


def test_render_baseline_contains_metrics_without_actual_payload() -> None:
    """验证基线保留指标，但不会写入完整模型结果。"""

    suite = RequirementEvaluationSuite(
        schema_version="1.0",
        cases=(_case(case_id="knowledge-ok"),),
    )
    report = evaluate_requirement_suite(
        suite,
        lambda _: OutfitRequirementAnalysis(
            intent=RequestIntent.KNOWLEDGE,
        ),
    )

    content = render_requirement_baseline(
        report,
        execution_date="2026-08-01",
        model_name="test-model",
    )

    assert "最终结果：1/1，通过率 100.0%" in content
    assert "| knowledge-ok | knowledge | PASS | - |" in content
    assert "test-model" in content
    assert '"intent"' not in content
