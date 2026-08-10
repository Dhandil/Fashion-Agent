"""衣物照片识别评测逻辑测试。"""

import json
from pathlib import Path

import httpx
import pytest

from app.agents.evaluation.wardrobe_vision import (
    VisionEvaluationCase,
    VisionEvaluationError,
    build_report,
    evaluate_prediction,
    load_vision_cases,
)


def test_load_vision_cases_resolves_relative_image_path(tmp_path: Path) -> None:
    manifest = tmp_path / "cases.json"
    manifest.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "case_id": "shirt-1",
                        "image_path": "images/shirt.jpg",
                        "expected": {"category": "衬衫", "colors": ["蓝色"]},
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    cases = load_vision_cases(manifest)

    assert cases[0].image_path == (tmp_path / "images/shirt.jpg").resolve()
    assert cases[0].expected["colors"] == ("蓝色",)


def test_evaluate_prediction_allows_more_specific_values() -> None:
    case = VisionEvaluationCase(
        case_id="shirt-1",
        image_path=Path("shirt.jpg"),
        expected={"category": ("衬衫",), "colors": ("蓝色",)},
    )

    result = evaluate_prediction(
        case,
        {"category": "休闲衬衫", "colors": ["浅蓝色"]},
    )

    assert result.passed is True
    assert result.matched_fields == ("category", "colors")
    assert result.failed_fields == ()


def test_build_report_marks_missing_expected_field_as_failure() -> None:
    case = VisionEvaluationCase(
        case_id="shirt-1",
        image_path=Path("shirt.jpg"),
        expected={"category": ("衬衫",), "materials": ("亚麻",)},
    )

    report = build_report((case,), {"shirt-1": {"category": "衬衫"}})

    assert report.total_count == 1
    assert report.passed_count == 0
    assert report.results[0].failed_fields == ("materials",)


def test_load_vision_cases_rejects_duplicate_case_id(tmp_path: Path) -> None:
    manifest = tmp_path / "cases.json"
    manifest.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "case_id": "same",
                        "image_path": "a.jpg",
                        "expected": {"category": "衬衫"},
                    },
                    {
                        "case_id": "same",
                        "image_path": "b.jpg",
                        "expected": {"category": "长裤"},
                    },
                ],
            },
        ),
        encoding="utf-8",
    )

    with pytest.raises(VisionEvaluationError, match="重复"):
        load_vision_cases(manifest)


def test_run_evaluation_sends_identity_and_returns_field_report(
    tmp_path: Path,
) -> None:
    from scripts.evaluate_wardrobe_vision import run_evaluation

    image_path = tmp_path / "shirt.jpg"
    image_path.write_bytes(b"fake-jpeg")
    case = VisionEvaluationCase(
        case_id="shirt-1",
        image_path=image_path,
        expected={"category": ("衬衫",)},
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["X-User-ID"] == "evaluation-user"
        return httpx.Response(
            200,
            json={"category": "休闲衬衫", "colors": [], "materials": []},
        )

    report = run_evaluation(
        (case,),
        base_url="http://testserver",
        user_id="evaluation-user",
        timeout=10,
        transport=httpx.MockTransport(handler),
    )

    assert report.passed_count == 1
