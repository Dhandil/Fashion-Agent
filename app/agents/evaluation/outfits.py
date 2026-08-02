"""结构化 Outfit 生成与单次修正评测。"""

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

from langchain_core.messages import HumanMessage, ToolMessage
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.agents.nodes.validate_outfit import validate_outfit
from app.agents.schemas.requirements import OutfitRequirementAnalysis
from app.agents.schemas.style_profile import (
    StyleProfileSnapshot,
)
from app.agents.state.shopping import ShoppingAgentState
from app.domain.entities.outfit import OutfitRecommendation
from app.domain.entities.outfit_validation import (
    OutfitFeasibilityReport,
    OutfitIssueCode,
)
from app.domain.entities.weather import WeatherContext

OutfitEvaluationMode = Literal["generation", "correction"]
CorrectionExpectation = Literal["allowed", "required", "forbidden"]
FinalDisposition = Literal["executable", "rejected"]
OutfitNode = Callable[
    [ShoppingAgentState],
    Mapping[str, Any],
]

_SOURCE_INTEGRITY_CODES = {
    OutfitIssueCode.UNKNOWN_SOURCE_ID,
    OutfitIssueCode.UNAVAILABLE_WARDROBE_ITEM,
    OutfitIssueCode.OUT_OF_STOCK_PRODUCT,
    OutfitIssueCode.DUPLICATE_SOURCE_ITEM,
}


class OutfitEvaluationExpectation(BaseModel):
    """一条案例对最终执行状态和修正行为的要求。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    final_disposition: FinalDisposition
    correction: CorrectionExpectation = "allowed"
    require_source_integrity: bool = True
    require_gap: bool = False
    gap_shopping_search_allowed: bool | None = None


class OutfitEvaluationCase(BaseModel):
    """包含受控动态事实的一条 Outfit 评测案例。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str = Field(min_length=1)
    category: Literal[
        "wardrobe",
        "weather",
        "shopping",
        "completeness",
        "source_integrity",
        "scenario",
        "preference",
    ]
    mode: OutfitEvaluationMode
    user_request: str = Field(min_length=1)
    requirement_analysis: OutfitRequirementAnalysis
    style_profile_snapshot: StyleProfileSnapshot | None = None
    wardrobe_records: tuple[dict[str, Any], ...] = ()
    product_records: tuple[dict[str, Any], ...] = ()
    weather_context: WeatherContext | None = None
    previous_outfit: OutfitRecommendation | None = None
    initial_outfit: OutfitRecommendation | None = None
    expected: OutfitEvaluationExpectation

    @model_validator(mode="after")
    def validate_mode_inputs(self) -> "OutfitEvaluationCase":
        """修正案例必须给出初始方案，生成案例则必须由模型生成。"""

        if self.mode == "correction" and self.initial_outfit is None:
            raise ValueError("correction 案例必须提供 initial_outfit。")
        if self.mode == "generation" and self.initial_outfit is not None:
            raise ValueError("generation 案例不能预置 initial_outfit。")
        return self


class OutfitEvaluationSuite(BaseModel):
    """可以提交 Git 的 Outfit 评测案例集。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = Field(min_length=1)
    cases: tuple[OutfitEvaluationCase, ...] = Field(
        min_length=1,
    )

    @model_validator(mode="after")
    def validate_unique_case_ids(self) -> "OutfitEvaluationSuite":
        """禁止重复案例 ID。"""

        case_ids = [case.case_id for case in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("Outfit 评测集中存在重复的 case_id。")
        return self


@dataclass(frozen=True, slots=True)
class OutfitCaseResult:
    """单条 Outfit 案例的闭环执行结果。"""

    case_id: str
    category: str
    mode: OutfitEvaluationMode
    passed: bool
    initial_outfit_produced: bool
    initial_executable: bool
    correction_attempted: bool
    correction_succeeded: bool
    final_disposition: FinalDisposition
    source_integrity: bool
    initial_issue_codes: tuple[OutfitIssueCode, ...]
    final_issue_codes: tuple[OutfitIssueCode, ...]
    mismatched_expectations: tuple[str, ...]
    gap_produced: bool = False
    expected_final_disposition: FinalDisposition = "executable"


@dataclass(frozen=True, slots=True)
class OutfitEvaluationReport:
    """Outfit 评测的业务指标汇总。"""

    results: tuple[OutfitCaseResult, ...]

    @property
    def total_count(self) -> int:
        return len(self.results)

    @property
    def passed_count(self) -> int:
        return sum(result.passed for result in self.results)

    @property
    def pass_rate(self) -> float:
        if not self.results:
            return 0.0
        return self.passed_count / self.total_count

    @property
    def initial_executable_count(self) -> int:
        return sum(
            result.initial_executable
            for result in self.results
            if result.mode == "generation" and result.expected_final_disposition == "executable"
        )

    @property
    def generation_count(self) -> int:
        """返回真正由模型生成初稿的案例数。"""

        return sum(
            result.mode == "generation" and result.expected_final_disposition == "executable"
            for result in self.results
        )

    @property
    def initial_pass_rate(self) -> float:
        if self.generation_count == 0:
            return 0.0
        return self.initial_executable_count / self.generation_count

    @property
    def correction_attempt_count(self) -> int:
        return sum(result.correction_attempted for result in self.results)

    @property
    def correction_success_count(self) -> int:
        return sum(result.correction_succeeded for result in self.results)

    @property
    def correction_success_rate(self) -> float:
        if self.correction_attempt_count == 0:
            return 0.0
        return self.correction_success_count / self.correction_attempt_count

    @property
    def source_integrity_count(self) -> int:
        return sum(result.source_integrity for result in self.results)

    @property
    def source_integrity_rate(self) -> float:
        if not self.results:
            return 0.0
        return self.source_integrity_count / self.total_count

    @property
    def rejected_count(self) -> int:
        return sum(result.final_disposition == "rejected" for result in self.results)


def load_outfit_evaluation_suite(
    path: Path,
) -> OutfitEvaluationSuite:
    """从 UTF-8 JSON 文件加载并校验 Outfit 案例。"""

    raw_data = json.loads(path.read_text(encoding="utf-8"))
    return OutfitEvaluationSuite.model_validate(raw_data)


def _append_tool_records(
    messages: list[Any],
    *,
    tool_name: str,
    records: tuple[dict[str, Any], ...],
) -> None:
    """把案例事实转换为节点能够读取的成功 ToolMessage。"""

    if not records:
        return
    messages.append(
        ToolMessage(
            content=json.dumps(
                records,
                ensure_ascii=False,
            ),
            tool_call_id=f"evaluation-{tool_name}",
            name=tool_name,
            status="success",
        ),
    )


def _create_case_state(
    case: OutfitEvaluationCase,
) -> ShoppingAgentState:
    """创建不包含真实用户数据的独立评测状态。"""

    messages: list[Any] = [
        HumanMessage(content=case.user_request),
    ]
    _append_tool_records(
        messages,
        tool_name="search_wardrobe",
        records=case.wardrobe_records,
    )
    _append_tool_records(
        messages,
        tool_name="search_products",
        records=case.product_records,
    )
    state: ShoppingAgentState = {
        "messages": messages,
        "requirement_analysis": case.requirement_analysis,
        "outfit_correction_attempts": 0,
    }
    if case.weather_context is not None:
        state["weather_context"] = case.weather_context
    if case.style_profile_snapshot is not None:
        state["style_profile_snapshot"] = case.style_profile_snapshot
    if case.previous_outfit is not None:
        state["previous_outfit_recommendation"] = case.previous_outfit
    return state


def _merge_state(
    state: ShoppingAgentState,
    updates: Mapping[str, Any],
) -> None:
    """把节点部分更新合并进评测状态。"""

    cast(dict[str, Any], state).update(updates)


def _issue_codes(
    report: OutfitFeasibilityReport | None,
) -> tuple[OutfitIssueCode, ...]:
    """提取稳定问题码供指标计算和报告输出。"""

    if report is None:
        return ()
    return tuple(issue.code for issue in report.issues)


def evaluate_outfit_case(
    case: OutfitEvaluationCase,
    *,
    generate_outfit: OutfitNode,
    correct_outfit: OutfitNode,
) -> OutfitCaseResult:
    """执行生成或预置初稿、检查、最多一次修正和复检。"""

    state = _create_case_state(case)
    if case.mode == "generation":
        _merge_state(state, generate_outfit(state))
    else:
        state["outfit_recommendation"] = case.initial_outfit

    initial_outfit_produced = state.get("outfit_recommendation") is not None
    gap_report = state.get("outfit_gap_report")
    gap_produced = gap_report is not None
    _merge_state(state, validate_outfit(state))
    initial_report = state.get("outfit_feasibility_report")
    initial_executable = bool(
        initial_report is not None
        and initial_report.is_executable
        and state.get("outfit_recommendation") is not None
    )

    correction_attempted = False
    if (
        state.get("outfit_recommendation") is not None
        and initial_report is not None
        and not initial_report.is_executable
    ):
        correction_attempted = True
        _merge_state(state, correct_outfit(state))
        _merge_state(state, validate_outfit(state))

    final_report = state.get("outfit_feasibility_report")
    final_executable = bool(
        final_report is not None
        and final_report.is_executable
        and state.get("outfit_recommendation") is not None
    )
    final_disposition: FinalDisposition = "executable" if final_executable else "rejected"
    final_issue_codes = _issue_codes(final_report)
    source_integrity = not any(code in _SOURCE_INTEGRITY_CODES for code in final_issue_codes)
    correction_succeeded = correction_attempted and final_executable

    expected = case.expected
    mismatches: list[str] = []
    if final_disposition != expected.final_disposition:
        mismatches.append("final_disposition")
    if expected.correction == "required" and not correction_attempted:
        mismatches.append("correction_required")
    if expected.correction == "forbidden" and correction_attempted:
        mismatches.append("correction_forbidden")
    if expected.require_source_integrity and not source_integrity:
        mismatches.append("source_integrity")
    if expected.require_gap and not gap_produced:
        mismatches.append("gap_required")
    if expected.gap_shopping_search_allowed is not None and (
        gap_report is None
        or gap_report.shopping_search_allowed is not expected.gap_shopping_search_allowed
    ):
        mismatches.append("gap_shopping_search_allowed")

    return OutfitCaseResult(
        case_id=case.case_id,
        category=case.category,
        mode=case.mode,
        passed=not mismatches,
        initial_outfit_produced=initial_outfit_produced,
        initial_executable=initial_executable,
        correction_attempted=correction_attempted,
        correction_succeeded=correction_succeeded,
        final_disposition=final_disposition,
        source_integrity=source_integrity,
        initial_issue_codes=_issue_codes(initial_report),
        final_issue_codes=final_issue_codes,
        mismatched_expectations=tuple(mismatches),
        gap_produced=gap_produced,
        expected_final_disposition=(expected.final_disposition),
    )


def evaluate_outfit_suite(
    suite: OutfitEvaluationSuite,
    *,
    generate_outfit: OutfitNode,
    correct_outfit: OutfitNode,
) -> OutfitEvaluationReport:
    """执行全部案例并汇总 Outfit 业务指标。"""

    return OutfitEvaluationReport(
        results=tuple(
            evaluate_outfit_case(
                case,
                generate_outfit=generate_outfit,
                correct_outfit=correct_outfit,
            )
            for case in suite.cases
        ),
    )


def render_outfit_baseline(
    report: OutfitEvaluationReport,
    *,
    execution_date: str,
    model_name: str,
) -> str:
    """生成不包含动态事实正文和模型原始响应的 Markdown 基线。"""

    lines = [
        "# Outfit 生成与修正基线",
        "",
        "## 基线信息",
        "",
        f"- 执行日期：{execution_date}",
        f"- 模型：`{model_name}`",
        f"- 案例数：{report.total_count}",
        f"- 案例通过率：{report.passed_count}/{report.total_count} ({report.pass_rate:.1%})",
        f"- 首次通过率：{report.initial_executable_count}/{report.generation_count} ({report.initial_pass_rate:.1%})",
        (
            f"- 修正成功率：{report.correction_success_count}/"
            f"{report.correction_attempt_count} ({report.correction_success_rate:.1%})"
        ),
        f"- 来源真实性：{report.source_integrity_count}/{report.total_count} ({report.source_integrity_rate:.1%})",
        f"- 最终拒绝数：{report.rejected_count}",
        "",
        "## 案例结果",
        "",
        "| case_id | 模式 | 首次通过 | 缺口 | 修正 | 最终状态 | 来源真实 | 结果 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    lines.extend(
        (
            f"| {result.case_id} | {result.mode} | "
            f"{'是' if result.initial_executable else '否'} | "
            f"{'是' if result.gap_produced else '否'} | "
            f"{'成功' if result.correction_succeeded else ('失败' if result.correction_attempted else '未执行')} | "
            f"{result.final_disposition} | "
            f"{'是' if result.source_integrity else '否'} | "
            f"{'PASS' if result.passed else 'FAIL'} |"
        )
        for result in report.results
    )
    lines.extend(
        [
            "",
            "该报告只保存聚合指标和稳定状态，不保存衣橱正文、商品正文、",
            "API Key 或完整模型响应。",
            "",
        ],
    )
    return "\n".join(lines)
