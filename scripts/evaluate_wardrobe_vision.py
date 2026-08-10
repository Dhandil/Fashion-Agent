"""运行衣物照片识别字段级评测；默认拒绝真实模型调用。"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import sys
from pathlib import Path
from typing import Any

import httpx

from app.agents.evaluation.wardrobe_vision import (
    VisionEvaluationCase,
    VisionEvaluationError,
    VisionEvaluationReport,
    build_report,
    load_vision_cases,
)

DEFAULT_MANIFEST = Path("evaluation/vision/cases.json")


def _content_type(image_path: Path) -> str:
    content_type, _ = mimetypes.guess_type(image_path.name)
    if content_type not in {"image/jpeg", "image/png"}:
        raise VisionEvaluationError(
            f"{image_path.name} 必须是 JPEG 或 PNG 文件。",
        )
    return content_type


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="运行衣物照片识别字段级评测。默认拒绝真实模型调用。",
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument(
        "--allow-model-call",
        action="store_true",
        help="明确允许向本地 API 发起真实视觉模型调用",
    )
    parser.add_argument("--case-id", action="append")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--user-id", default="fashion-agent-vision-evaluation")
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def _select_cases(
    cases: tuple[VisionEvaluationCase, ...],
    case_ids: list[str] | None,
) -> tuple[VisionEvaluationCase, ...]:
    if not case_ids:
        return cases
    selected = tuple(case for case in cases if case.case_id in set(case_ids))
    missing = set(case_ids) - {case.case_id for case in selected}
    if missing:
        raise VisionEvaluationError("未找到评测案例：" + ", ".join(sorted(missing)))
    return selected


def _request_prediction(
    client: httpx.Client,
    case: VisionEvaluationCase,
) -> dict[str, Any]:
    if not case.image_path.is_file():
        raise VisionEvaluationError(f"找不到图片文件：{case.image_path}")
    encoded = base64.b64encode(case.image_path.read_bytes()).decode("ascii")
    response = client.post(
        "/api/v1/wardrobe/recognitions",
        headers={"X-User-ID": client.headers.get("X-User-ID", "")},
        json={
            "image_base64": encoded,
            "content_type": _content_type(case.image_path),
        },
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise VisionEvaluationError("识别响应不是 JSON 对象。")
    return payload


def run_evaluation(
    cases: tuple[VisionEvaluationCase, ...],
    *,
    base_url: str,
    user_id: str,
    timeout: float,
    transport: httpx.BaseTransport | None = None,
) -> VisionEvaluationReport:
    """调用识别 API 并返回不含模型原始文本的字段级报告。"""

    predictions: dict[str, dict[str, Any]] = {}
    with httpx.Client(
        base_url=base_url.rstrip("/"),
        timeout=timeout,
        headers={"X-User-ID": user_id},
        transport=transport,
        trust_env=False,
    ) as client:
        for case in cases:
            predictions[case.case_id] = _request_prediction(client, case)
    return build_report(cases, predictions)


def _write_report(path: Path, report: VisionEvaluationReport) -> None:
    payload = {
        "schema_version": "1.0",
        "total_count": report.total_count,
        "passed_count": report.passed_count,
        "pass_rate": report.pass_rate,
        "cases": [
            {
                "case_id": result.case_id,
                "passed": result.passed,
                "matched_fields": result.matched_fields,
                "failed_fields": result.failed_fields,
            }
            for result in report.results
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    args = _parse_args()
    if not args.allow_model_call:
        print(
            "[拒绝] 评测会调用真实视觉模型，请显式提供 --allow-model-call。",
            file=sys.stderr,
        )
        return 2

    try:
        cases = _select_cases(load_vision_cases(args.manifest), args.case_id)
        report = run_evaluation(
            cases,
            base_url=args.base_url,
            user_id=args.user_id,
            timeout=args.timeout,
        )
    except (VisionEvaluationError, OSError, httpx.HTTPError, ValueError) as exc:
        print(f"[失败] 视觉评测未通过：{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    for result in report.results:
        status = "PASS" if result.passed else "FAIL"
        print(
            f"[{status}] {result.case_id} "
            f"matched={','.join(result.matched_fields) or 'none'} "
            f"failed={','.join(result.failed_fields) or 'none'}",
        )
    print(
        f"视觉识别评测完成：通过={report.passed_count}/{report.total_count}，"
        f"通过率={report.pass_rate:.1%}。",
    )
    if args.output:
        _write_report(args.output, report)
        print(f"报告已写入：{args.output}")
    return 0 if report.passed_count == report.total_count else 1


if __name__ == "__main__":
    raise SystemExit(main())
