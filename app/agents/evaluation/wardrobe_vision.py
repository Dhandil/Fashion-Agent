"""衣物照片识别的字段级质量评测。"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

VISION_FIELDS = ("category", "colors", "materials")


class VisionEvaluationError(ValueError):
    """评测清单或识别结果不符合约定结构。"""


@dataclass(frozen=True, slots=True)
class VisionContractResult:
    """一次无需人工标注的结构化输出契约检查结果。"""

    passed: bool
    item_count: int
    errors: tuple[str, ...]


def validate_vision_contract(
    payload: Mapping[str, object],
    *,
    max_items: int = 8,
) -> VisionContractResult:
    """检查单件或批量识别响应的安全边界，不判断穿衣识别准确率。"""

    raw_items = payload.get("items", payload)
    if isinstance(raw_items, Mapping):
        items: list[object] = [raw_items]
    elif isinstance(raw_items, list):
        items = raw_items
    else:
        return VisionContractResult(False, 0, ("items 必须是对象或数组",))

    errors: list[str] = []
    if not items:
        errors.append("识别结果不能为空")
    if len(items) > max_items:
        errors.append("识别结果超过单张照片数量上限")

    draft_ids: set[str] = set()
    for index, item in enumerate(items):
        if not isinstance(item, Mapping):
            errors.append(f"第 {index + 1} 项不是对象")
            continue
        draft_id = item.get("draft_id")
        if not isinstance(draft_id, str) or not draft_id:
            errors.append(f"第 {index + 1} 项缺少 draft_id")
        elif draft_id in draft_ids:
            errors.append(f"draft_id 重复：{draft_id}")
        else:
            draft_ids.add(draft_id)

        if item.get("requires_confirmation") is not True:
            errors.append(f"第 {index + 1} 项必须要求用户确认")
        confidence = item.get("confidence")
        if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
            errors.append(f"第 {index + 1} 项 confidence 无效")

        missing_fields = _as_values(item.get("missing_fields"))
        uncertain_fields = _as_values(item.get("uncertain_fields"))
        for field_name, values in (
            ("missing_fields", missing_fields),
            ("uncertain_fields", uncertain_fields),
        ):
            raw_value = item.get(field_name)
            if not isinstance(raw_value, list) or any(
                not isinstance(value, str) for value in raw_value
            ):
                errors.append(f"第 {index + 1} 项 {field_name} 格式无效")

        for field_name in ("name", "category"):
            value = item.get(field_name)
            if (
                (not isinstance(value, str) or not value.strip())
                and field_name not in missing_fields
            ):
                errors.append(
                    f"第 {index + 1} 项 {field_name} 为空但未声明缺失",
                )

    return VisionContractResult(
        passed=not errors,
        item_count=len(items),
        errors=tuple(errors),
    )


@dataclass(frozen=True, slots=True)
class VisionEvaluationCase:
    """一张照片和人工标注的可评测字段。"""

    case_id: str
    image_path: Path
    expected: Mapping[str, tuple[str, ...]]


@dataclass(frozen=True, slots=True)
class VisionEvaluationResult:
    """单个案例的字段级结果，不保存模型原始文本。"""

    case_id: str
    passed: bool
    matched_fields: tuple[str, ...]
    failed_fields: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class VisionEvaluationReport:
    """整组照片的聚合结果。"""

    results: tuple[VisionEvaluationResult, ...]

    @property
    def total_count(self) -> int:
        return len(self.results)

    @property
    def passed_count(self) -> int:
        return sum(result.passed for result in self.results)

    @property
    def pass_rate(self) -> float:
        return self.passed_count / self.total_count if self.total_count else 0.0


def _as_values(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, Sequence) and not isinstance(value, bytes | bytearray):
        return tuple(item for item in value if isinstance(item, str))
    return ()


def _normalize(value: str) -> str:
    return "".join(value.casefold().split())


def _validate_expected(expected: object) -> dict[str, tuple[str, ...]]:
    if not isinstance(expected, Mapping):
        raise VisionEvaluationError("expected 必须是对象。")

    normalized: dict[str, tuple[str, ...]] = {}
    for field_name, value in expected.items():
        if field_name not in VISION_FIELDS:
            raise VisionEvaluationError(f"不支持的评测字段：{field_name}")
        values = _as_values(value)
        if not values or any(not item.strip() for item in values):
            raise VisionEvaluationError(f"评测字段 {field_name} 不能为空。")
        normalized[field_name] = values
    if not normalized:
        raise VisionEvaluationError("每个案例至少需要一个 expected 字段。")
    return normalized


def load_vision_cases(path: Path) -> tuple[VisionEvaluationCase, ...]:
    """加载照片评测清单；图片路径相对于清单文件所在目录。"""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VisionEvaluationError(f"无法读取评测清单：{path}") from exc

    raw_cases = payload.get("cases") if isinstance(payload, Mapping) else None
    if not isinstance(raw_cases, list) or not raw_cases:
        raise VisionEvaluationError("评测清单 cases 必须是非空数组。")

    cases: list[VisionEvaluationCase] = []
    seen_ids: set[str] = set()
    for raw_case in raw_cases:
        if not isinstance(raw_case, Mapping):
            raise VisionEvaluationError("评测案例必须是对象。")
        case_id = raw_case.get("case_id")
        image_path = raw_case.get("image_path")
        if not isinstance(case_id, str) or not case_id.strip():
            raise VisionEvaluationError("评测案例缺少 case_id。")
        if case_id in seen_ids:
            raise VisionEvaluationError(f"评测案例 ID 重复：{case_id}")
        if not isinstance(image_path, str) or not image_path.strip():
            raise VisionEvaluationError(f"评测案例 {case_id} 缺少 image_path。")
        seen_ids.add(case_id)
        cases.append(
            VisionEvaluationCase(
                case_id=case_id,
                image_path=(path.parent / image_path).resolve(),
                expected=_validate_expected(raw_case.get("expected")),
            ),
        )
    return tuple(cases)


def evaluate_prediction(
    case: VisionEvaluationCase,
    prediction: Mapping[str, object],
) -> VisionEvaluationResult:
    """比较人工标注和模型结构化字段，允许模型返回更具体的描述。"""

    matched: list[str] = []
    failed: list[str] = []
    for field_name, expected_values in case.expected.items():
        actual_values = tuple(_normalize(item) for item in _as_values(prediction.get(field_name)))
        if all(
            any(_normalize(expected) in actual for actual in actual_values)
            for expected in expected_values
        ):
            matched.append(field_name)
        else:
            failed.append(field_name)

    return VisionEvaluationResult(
        case_id=case.case_id,
        passed=not failed,
        matched_fields=tuple(matched),
        failed_fields=tuple(failed),
    )


def build_report(
    cases: Sequence[VisionEvaluationCase],
    predictions: Mapping[str, Mapping[str, object]],
) -> VisionEvaluationReport:
    """根据案例和结构化预测构造聚合报告。"""

    results = tuple(
        evaluate_prediction(case, predictions.get(case.case_id, {}))
        for case in cases
    )
    return VisionEvaluationReport(results=results)
