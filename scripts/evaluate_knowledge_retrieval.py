import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from app.rag.evaluation.retrieval import (
    RetrievalEvaluationReport,
    evaluate_retrieval_suite,
    load_retrieval_evaluation_suite,
)
from app.rag.retrievers.provider import get_knowledge_retriever

DEFAULT_EVALUATION_PATH = Path(
    "evaluation/rag/retrieval_cases.json",
)
DEFAULT_REPORT_DIR = Path(
    "evaluation/reports",
)


def _print_report(report: RetrievalEvaluationReport) -> None:
    """输出每条问题的结果和实际命中来源，方便人工定位。"""

    for result in report.results:
        status = "PASS" if result.passed else "FAIL"
        print(
            f"[{status}] {result.case_id} "
            f"knowledge_rank={result.knowledge_rank} "
            f"section_rank={result.section_rank}",
        )

        if not result.returned_sources:
            print("  - 未命中任何知识来源")
            continue

        for source in result.returned_sources:
            print(
                f"  - fragment_id={source.fragment_id}, source={source.source_path_or_url}",
            )

    print(
        "检索评测完成："
        f"release={report.release_id}，"
        f"通过={report.passed_count}/{report.total_count}，"
        f"通过率={report.pass_rate:.1%}。",
    )


def _serialize_report(
    report: RetrievalEvaluationReport,
    *,
    min_pass_rate: float,
) -> dict[str, object]:
    """把评测报告序列化为可提交的 JSON 结构。"""

    return {
        "schema_version": "1.0",
        "release_id": report.release_id,
        "generated_at": datetime.now(UTC).isoformat(),
        "total_count": report.total_count,
        "passed_count": report.passed_count,
        "pass_rate": report.pass_rate,
        "min_pass_rate": min_pass_rate,
        "results": [
            {
                "case_id": result.case_id,
                "passed": result.passed,
                "knowledge_rank": result.knowledge_rank,
                "section_rank": result.section_rank,
                "returned_sources": [
                    {
                        "fragment_id": source.fragment_id,
                        "source": source.source_path_or_url,
                    }
                    for source in result.returned_sources
                ],
            }
            for result in report.results
        ],
    }


def _write_report(
    report: RetrievalEvaluationReport,
    *,
    min_pass_rate: float,
    report_dir: Path,
) -> Path:
    """把评测报告写入 evaluation/reports/，返回报告路径。"""

    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"retrieval_{report.release_id}.json"
    report_path.write_text(
        json.dumps(
            _serialize_report(
                report,
                min_pass_rate=min_pass_rate,
            ),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return report_path


def parse_args() -> argparse.Namespace:
    """解析评测参数。"""

    parser = argparse.ArgumentParser(
        description="运行知识检索评测并保存质量报告。",
    )
    parser.add_argument(
        "--cases",
        type=Path,
        default=DEFAULT_EVALUATION_PATH,
        help="评测问题集路径（默认 evaluation/rag/retrieval_cases.json）。",
    )
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=DEFAULT_REPORT_DIR,
        help="评测报告输出目录（默认 evaluation/reports）。",
    )
    parser.add_argument(
        "--min-pass-rate",
        type=float,
        default=1.0,
        help="通过率下限，低于该值退出码为 1（默认 1.0）。",
    )
    report_group = parser.add_mutually_exclusive_group()
    report_group.add_argument(
        "--write-report",
        action="store_true",
        help="显式覆盖 evaluation/reports 中对应的评测基线文件。",
    )
    report_group.add_argument(
        "--no-write",
        dest="write_report",
        action="store_false",
        help="只运行评测并输出结果（默认行为）。",
    )
    parser.set_defaults(write_report=False)
    return parser.parse_args()


def main() -> None:
    """使用当前只读 Chroma 集合运行正式知识检索评测并保存报告。"""

    args = parse_args()
    suite = load_retrieval_evaluation_suite(
        args.cases,
    )
    retriever = get_knowledge_retriever()
    report = evaluate_retrieval_suite(
        suite=suite,
        retrieve_documents=retriever.invoke,
    )
    _print_report(report)
    if args.write_report:
        report_path = _write_report(
            report,
            min_pass_rate=args.min_pass_rate,
            report_dir=args.report_dir,
        )
        print(f"评测报告已保存：{report_path}")
    else:
        print("已使用只读模式，不覆盖评测基线文件。")

    # 非零退出码便于在 CI 或发布流程中阻止检索质量回退。
    if report.pass_rate < args.min_pass_rate:
        print(
            f"评测未达门禁：通过率 {report.pass_rate:.1%} < {args.min_pass_rate:.1%}。",
        )
        raise SystemExit(1)


if __name__ == "__main__":
    main()
