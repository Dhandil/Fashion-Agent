"""检查衣物视觉识别响应的结构化安全契约，不调用外部模型。"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from pathlib import Path

from app.agents.evaluation.wardrobe_vision import (
    VisionEvaluationError,
    validate_vision_contract,
)

DEFAULT_CASES = Path("evaluation/vision/contract_cases.json")


def _load_cases(path: Path) -> list[Mapping[str, object]]:
    """读取契约样例并保证每项都有明确的预期结果。"""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VisionEvaluationError(f"无法读取契约样例：{path}") from exc
    cases = payload.get("cases") if isinstance(payload, Mapping) else None
    if not isinstance(cases, list) or not cases:
        raise VisionEvaluationError("契约样例 cases 必须是非空数组")
    return [case for case in cases if isinstance(case, Mapping)]


def main() -> int:
    """运行本地结构契约检查并输出摘要。"""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    args = parser.parse_args()

    try:
        cases = _load_cases(args.cases)
        for case in cases:
            result = validate_vision_contract(case.get("payload", {}))
            expected = case.get("expected_valid") is True
            actual = result.passed == expected
            status = "PASS" if actual else "FAIL"
            print(
                f"[{status}] {case.get('case_id', '<unknown>')} "
                f"items={result.item_count} "
                f"errors={','.join(result.errors) or 'none'}",
            )
            if not actual:
                return 1
    except VisionEvaluationError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
