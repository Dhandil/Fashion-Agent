"""使用当前模型运行结构化需求分析评测。"""

import argparse
from datetime import UTC, datetime
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage

from app.agents.evaluation.requirements import (
    RequirementEvaluationCase,
    RequirementEvaluationReport,
    RequirementEvaluationSuite,
    evaluate_requirement_suite,
    load_requirement_evaluation_suite,
    render_requirement_baseline,
)
from app.agents.nodes.analyze_requirements import (
    create_requirement_analysis_node,
)
from app.agents.schemas.requirements import OutfitRequirementAnalysis
from app.agents.state.shopping import ShoppingAgentState
from app.core.config import get_settings
from app.llm.providers.openai_compatible import create_chat_model

DEFAULT_EVALUATION_PATH = Path(
    "evaluation/agents/requirement_cases.json",
)


def _parse_args() -> argparse.Namespace:
    """读取可选基线输出路径。"""

    parser = argparse.ArgumentParser(
        description="运行结构化需求分析评测。",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="可选的 Markdown 基线输出路径。",
    )
    parser.add_argument(
        "--case-id",
        action="append",
        help="只执行指定案例；可以重复传入多个 case_id。",
    )
    return parser.parse_args()


def _print_report(report: RequirementEvaluationReport) -> None:
    """输出字段差异、实际结果和分类通过率。"""

    for result in report.results:
        status = "PASS" if result.passed else "FAIL"
        mismatches = ",".join(result.mismatched_fields) or "none"
        print(
            f"[{status}] {result.case_id} category={result.category} mismatches={mismatches}",
        )
        if not result.passed:
            print(
                "  - actual=" + result.actual.model_dump_json(),
            )

    for category_result in report.category_results:
        print(
            "分类结果："
            f"{category_result.category}="
            f"{category_result.passed_count}/"
            f"{category_result.total_count} "
            f"({category_result.pass_rate:.1%})",
        )

    print(
        "需求分析评测完成："
        f"通过={report.passed_count}/{report.total_count}，"
        f"通过率={report.pass_rate:.1%}。",
    )


def main() -> None:
    """加载可提交案例并使用真实需求分析节点执行评测。"""

    args = _parse_args()
    suite = load_requirement_evaluation_suite(
        DEFAULT_EVALUATION_PATH,
    )
    if args.case_id:
        selected_ids = set(args.case_id)
        selected_cases = tuple(case for case in suite.cases if case.case_id in selected_ids)
        found_ids = {case.case_id for case in selected_cases}
        missing_ids = selected_ids - found_ids
        if missing_ids:
            raise SystemExit(
                "未找到评测案例：" + ", ".join(sorted(missing_ids)),
            )
        suite = RequirementEvaluationSuite(
            schema_version=suite.schema_version,
            cases=selected_cases,
        )
    settings = get_settings()
    model = create_chat_model(settings)
    analysis_node = create_requirement_analysis_node(model)

    def analyze_case(
        case: RequirementEvaluationCase,
    ) -> OutfitRequirementAnalysis:
        """把评测消息转换为真实节点使用的 LangChain 消息。"""

        state: ShoppingAgentState = {
            "messages": [
                (
                    HumanMessage(content=message.content)
                    if message.role == "user"
                    else AIMessage(content=message.content)
                )
                for message in case.messages
            ],
        }
        return analysis_node(state)["requirement_analysis"]

    report = evaluate_requirement_suite(
        suite,
        analyze_case,
    )
    _print_report(report)
    if args.output is not None:
        args.output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        args.output.write_text(
            render_requirement_baseline(
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
