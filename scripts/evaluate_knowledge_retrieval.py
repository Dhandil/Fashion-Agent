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


def main() -> None:
    """使用当前只读 Chroma 集合运行正式知识检索评测。"""

    suite = load_retrieval_evaluation_suite(
        DEFAULT_EVALUATION_PATH,
    )
    retriever = get_knowledge_retriever()
    report = evaluate_retrieval_suite(
        suite=suite,
        retrieve_documents=retriever.invoke,
    )
    _print_report(report)

    # 非零退出码便于未来在 CI 或发布流程中阻止检索质量回退。
    if report.passed_count != report.total_count:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
