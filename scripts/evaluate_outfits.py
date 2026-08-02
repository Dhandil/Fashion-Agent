"""使用当前模型运行 Outfit 生成与修正评测。"""

import argparse
from datetime import UTC, datetime
from pathlib import Path

from app.agents.context_package import ContextBudgetPolicy
from app.agents.evaluation.outfits import (
    OutfitEvaluationReport,
    OutfitEvaluationSuite,
    evaluate_outfit_suite,
    load_outfit_evaluation_suite,
    render_outfit_baseline,
)
from app.agents.nodes.correct_outfit import create_outfit_correction_node
from app.agents.nodes.generate_outfit import create_outfit_generation_node
from app.core.config import get_settings
from app.llm.providers.openai_compatible import create_chat_model

DEFAULT_EVALUATION_PATH = Path(
    "evaluation/agents/outfit_cases.json",
)


def _parse_args() -> argparse.Namespace:
    """读取案例筛选和可选报告输出路径。"""

    parser = argparse.ArgumentParser(
        description="运行 Outfit 生成与修正评测。",
    )
    parser.add_argument(
        "--case-id",
        action="append",
        help="只执行指定案例；可以重复传入多个 case_id。",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="可选的 Markdown 基线输出路径。",
    )
    return parser.parse_args()


def _select_cases(
    suite: OutfitEvaluationSuite,
    case_ids: list[str] | None,
) -> OutfitEvaluationSuite:
    """按稳定案例 ID 选择子集，并拒绝拼写错误。"""

    if not case_ids:
        return suite
    selected_ids = set(case_ids)
    selected_cases = tuple(case for case in suite.cases if case.case_id in selected_ids)
    found_ids = {case.case_id for case in selected_cases}
    missing_ids = selected_ids - found_ids
    if missing_ids:
        raise SystemExit(
            "未找到评测案例：" + ", ".join(sorted(missing_ids)),
        )
    return OutfitEvaluationSuite(
        schema_version=suite.schema_version,
        cases=selected_cases,
    )


def _print_report(report: OutfitEvaluationReport) -> None:
    """输出单案例状态和四项核心业务指标。"""

    for result in report.results:
        status = "PASS" if result.passed else "FAIL"
        mismatches = (
            ",".join(
                result.mismatched_expectations,
            )
            or "none"
        )
        print(
            f"[{status}] {result.case_id} "
            f"initial={result.initial_executable} "
            f"gap={result.gap_produced} "
            f"corrected={result.correction_succeeded} "
            f"final={result.final_disposition} "
            f"source_integrity={result.source_integrity} "
            f"mismatches={mismatches}",
        )
        if result.final_issue_codes:
            print(
                "  - final_issues=" + ",".join(code.value for code in result.final_issue_codes),
            )

    print(
        "Outfit 评测完成："
        f"通过={report.passed_count}/{report.total_count}，"
        f"首次通过率={report.initial_pass_rate:.1%}，"
        f"修正成功率={report.correction_success_rate:.1%}，"
        f"来源真实性={report.source_integrity_rate:.1%}，"
        f"最终拒绝={report.rejected_count}。",
    )


def main() -> None:
    """运行真实结构化生成和受限修正节点。"""

    args = _parse_args()
    suite = _select_cases(
        load_outfit_evaluation_suite(
            DEFAULT_EVALUATION_PATH,
        ),
        args.case_id,
    )
    settings = get_settings()
    model = create_chat_model(settings)
    context_budget_policy = ContextBudgetPolicy(
        total_max_chars=settings.agent_context_max_chars,
        explicit_memory_max_chars=(settings.agent_explicit_memory_max_chars),
        historical_memory_max_chars=(settings.agent_historical_memory_max_chars),
        knowledge_max_chars=settings.agent_knowledge_max_chars,
    )
    report = evaluate_outfit_suite(
        suite,
        generate_outfit=create_outfit_generation_node(
            model,
            context_budget_policy=context_budget_policy,
        ),
        correct_outfit=create_outfit_correction_node(
            model,
            context_budget_policy=context_budget_policy,
        ),
    )
    _print_report(report)

    if args.output is not None:
        args.output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        args.output.write_text(
            render_outfit_baseline(
                report,
                execution_date=datetime.now(UTC).date().isoformat(),
                model_name=settings.llm_model or "未配置",
            ),
            encoding="utf-8",
        )
        print(f"基线已写入：{args.output}")

    if report.passed_count != report.total_count:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
