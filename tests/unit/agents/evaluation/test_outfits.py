"""Outfit 生成与修正评测测试。"""

from pathlib import Path
from unittest.mock import Mock

from app.agents.evaluation.outfits import (
    OutfitCaseResult,
    OutfitEvaluationCase,
    OutfitEvaluationExpectation,
    OutfitEvaluationReport,
    OutfitEvaluationSuite,
    evaluate_outfit_case,
    evaluate_outfit_suite,
    load_outfit_evaluation_suite,
    render_outfit_baseline,
)
from app.domain.entities.outfit import OutfitItem, OutfitRecommendation


def _valid_outfit() -> OutfitRecommendation:
    """创建只引用当前衣橱事实的完整方案。"""

    return OutfitRecommendation(
        name="完整通勤方案",
        scenario="通勤",
        items=(
            OutfitItem(
                role="上装",
                name="白色衬衫",
                source="wardrobe",
                source_reference_id="upper-001",
            ),
            OutfitItem(
                role="下装",
                name="黑色长裤",
                source="wardrobe",
                source_reference_id="lower-001",
            ),
            OutfitItem(
                role="鞋履",
                name="黑色皮鞋",
                source="wardrobe",
                source_reference_id="shoes-001",
            ),
        ),
        recommendation_reason="适合通勤。",
    )


def _case(
    *,
    mode: str,
    expected_disposition: str = "executable",
    initial_outfit: OutfitRecommendation | None = None,
) -> OutfitEvaluationCase:
    """创建包含三个真实衣橱 ID 的最小案例。"""

    return OutfitEvaluationCase.model_validate(
        {
            "case_id": f"test-{mode}",
            "category": "completeness",
            "mode": mode,
            "user_request": "用我的衣橱搭配通勤服装",
            "requirement_analysis": {
                "intent": "outfit",
                "scenario": "通勤",
                "needs_wardrobe": True,
            },
            "wardrobe_records": [
                {
                    "wardrobe_item_id": "upper-001",
                    "name": "白色衬衫",
                    "status": "available",
                },
                {
                    "wardrobe_item_id": "lower-001",
                    "name": "黑色长裤",
                    "status": "available",
                },
                {
                    "wardrobe_item_id": "shoes-001",
                    "name": "黑色皮鞋",
                    "status": "available",
                },
            ],
            "initial_outfit": (
                initial_outfit.model_dump(mode="json") if initial_outfit is not None else None
            ),
            "expected": {
                "final_disposition": expected_disposition,
                "correction": ("required" if mode == "correction" else "forbidden"),
            },
        },
    )


def test_committed_suite_covers_generation_and_correction() -> None:
    """验证正式案例同时覆盖生成、修正和关键事实类别。"""

    suite = load_outfit_evaluation_suite(
        Path("evaluation/agents/outfit_cases.json"),
    )

    assert len(suite.cases) == 6
    assert {case.mode for case in suite.cases} == {
        "generation",
        "correction",
    }
    assert {case.category for case in suite.cases} == {
        "wardrobe",
        "weather",
        "shopping",
        "completeness",
        "source_integrity",
        "scenario",
    }


def test_generation_first_pass_reports_no_correction() -> None:
    """验证初稿通过时不会调用修正节点。"""

    generate = Mock(
        return_value={
            "outfit_recommendation": _valid_outfit(),
        },
    )
    correct = Mock()

    result = evaluate_outfit_case(
        _case(mode="generation"),
        generate_outfit=generate,
        correct_outfit=correct,
    )

    assert result.passed is True
    assert result.initial_executable is True
    assert result.correction_attempted is False
    assert result.source_integrity is True
    correct.assert_not_called()


def test_invalid_initial_outfit_can_be_corrected_once() -> None:
    """验证缺少核心角色的初稿经过一次修正后计为成功。"""

    incomplete = OutfitRecommendation(
        name="不完整方案",
        scenario="通勤",
        items=(
            OutfitItem(
                role="上装",
                name="白色衬衫",
                source="wardrobe",
                source_reference_id="upper-001",
            ),
        ),
        recommendation_reason="缺少下装和鞋履。",
    )
    correct = Mock(
        return_value={
            "outfit_recommendation": _valid_outfit(),
            "outfit_correction_attempts": 1,
        },
    )

    result = evaluate_outfit_case(
        _case(
            mode="correction",
            initial_outfit=incomplete,
        ),
        generate_outfit=Mock(),
        correct_outfit=correct,
    )

    assert result.passed is True
    assert result.initial_executable is False
    assert result.correction_attempted is True
    assert result.correction_succeeded is True
    assert result.final_disposition == "executable"
    correct.assert_called_once()


def test_second_invalid_outfit_is_rejected() -> None:
    """验证修正后仍引用虚构 ID 时计为最终拒绝。"""

    invalid = OutfitRecommendation(
        name="虚构来源方案",
        scenario="通勤",
        items=(
            OutfitItem(
                role="上装",
                name="虚构衬衫",
                source="wardrobe",
                source_reference_id="invented-999",
            ),
            *_valid_outfit().items[1:],
        ),
        recommendation_reason="包含虚构来源。",
    )
    case = _case(
        mode="correction",
        expected_disposition="rejected",
        initial_outfit=invalid,
    ).model_copy(
        update={
            "expected": OutfitEvaluationExpectation(
                final_disposition="rejected",
                correction="required",
                require_source_integrity=False,
            ),
        },
    )

    # 修正节点返回原错误方案，第二次检查必须拒绝。
    result = evaluate_outfit_case(
        case,
        generate_outfit=Mock(),
        correct_outfit=Mock(
            return_value={
                "outfit_recommendation": invalid,
                "outfit_correction_attempts": 1,
            },
        ),
    )

    assert result.passed is True
    assert result.final_disposition == "rejected"
    assert result.source_integrity is False
    assert "unknown_source_id" in result.final_issue_codes


def test_suite_metrics_and_baseline_are_aggregated() -> None:
    """验证指标分母和可提交基线内容保持稳定。"""

    suite = OutfitEvaluationSuite(
        schema_version="1.0",
        cases=(_case(mode="generation"),),
    )
    report = evaluate_outfit_suite(
        suite,
        generate_outfit=Mock(
            return_value={
                "outfit_recommendation": _valid_outfit(),
            },
        ),
        correct_outfit=Mock(),
    )

    assert report.total_count == 1
    assert report.initial_pass_rate == 1.0
    assert report.source_integrity_rate == 1.0
    content = render_outfit_baseline(
        report,
        execution_date="2026-08-01",
        model_name="test-model",
    )
    assert "案例通过率：1/1 (100.0%)" in content
    assert "来源真实性：1/1 (100.0%)" in content


def test_initial_pass_rate_excludes_preloaded_correction_cases() -> None:
    """验证刻意错误的修正案例不会降低生成初稿通过率。"""

    common_values = {
        "category": "completeness",
        "passed": True,
        "source_integrity": True,
        "initial_issue_codes": (),
        "final_issue_codes": (),
        "mismatched_expectations": (),
    }
    report = OutfitEvaluationReport(
        results=(
            OutfitCaseResult(
                case_id="generation-pass",
                mode="generation",
                initial_outfit_produced=True,
                initial_executable=True,
                correction_attempted=False,
                correction_succeeded=False,
                final_disposition="executable",
                **common_values,
            ),
            OutfitCaseResult(
                case_id="preloaded-correction",
                mode="correction",
                initial_outfit_produced=True,
                initial_executable=False,
                correction_attempted=True,
                correction_succeeded=True,
                final_disposition="executable",
                **common_values,
            ),
        ),
    )

    assert report.generation_count == 1
    assert report.initial_executable_count == 1
    assert report.initial_pass_rate == 1.0
