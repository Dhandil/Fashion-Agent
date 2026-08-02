"""结构化需求分析的可重复评测。"""

import json
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.agents.schemas.requirements import (
    OutfitRequirementAnalysis,
    RequestIntent,
    RequirementField,
    ShoppingIntent,
)


class RequirementEvaluationMessage(BaseModel):
    """评测案例中的一条非敏感对话消息。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)


class RequirementEvaluationExpectation(BaseModel):
    """一条案例需要满足的结构化结果子集。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    intent: RequestIntent
    is_sufficient: bool
    needs_wardrobe: bool
    needs_weather: bool
    shopping_intent: ShoppingIntent
    missing_fields_contains: tuple[RequirementField, ...] = ()
    # `None` 表示案例不检查该字段；显式 `[]` 表示要求结果必须为空。
    style_preferences: tuple[str, ...] | None = None
    color_preferences: tuple[str, ...] | None = None
    avoided_styles: tuple[str, ...] | None = None
    avoided_colors: tuple[str, ...] | None = None
    avoided_materials: tuple[str, ...] | None = None


class RequirementEvaluationCase(BaseModel):
    """单条需求理解评测案例。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str = Field(min_length=1)
    category: Literal[
        "knowledge",
        "incomplete",
        "wardrobe",
        "adjustment",
        "shopping",
        "shopping_boundary",
        "weather_boundary",
        "preference_boundary",
    ]
    messages: tuple[RequirementEvaluationMessage, ...] = Field(
        min_length=1,
    )
    expected: RequirementEvaluationExpectation

    @model_validator(mode="after")
    def validate_last_message_is_user(self) -> "RequirementEvaluationCase":
        """保证评测输入最后一条消息代表当前用户请求。"""

        if self.messages[-1].role != "user":
            raise ValueError("评测案例最后一条消息必须来自用户。")
        return self


class RequirementEvaluationSuite(BaseModel):
    """可以提交 Git 的需求分析评测集。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = Field(min_length=1)
    cases: tuple[RequirementEvaluationCase, ...] = Field(
        min_length=1,
    )

    @model_validator(mode="after")
    def validate_unique_case_ids(self) -> "RequirementEvaluationSuite":
        """禁止重复案例 ID，避免聚合结果产生歧义。"""

        case_ids = [case.case_id for case in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("需求分析评测集中存在重复的 case_id。")
        return self


@dataclass(frozen=True, slots=True)
class RequirementCaseResult:
    """单条案例的字段级评分结果。"""

    case_id: str
    category: str
    passed: bool
    mismatched_fields: tuple[str, ...]
    actual: OutfitRequirementAnalysis


@dataclass(frozen=True, slots=True)
class RequirementCategoryResult:
    """一个需求类别的聚合通过率。"""

    category: str
    total_count: int
    passed_count: int

    @property
    def pass_rate(self) -> float:
        """返回当前类别的通过率。"""

        if self.total_count == 0:
            return 0.0
        return self.passed_count / self.total_count


@dataclass(frozen=True, slots=True)
class RequirementEvaluationReport:
    """完整需求分析评测报告。"""

    results: tuple[RequirementCaseResult, ...]

    @property
    def total_count(self) -> int:
        """返回案例总数。"""

        return len(self.results)

    @property
    def passed_count(self) -> int:
        """返回完全匹配预期的案例数。"""

        return sum(result.passed for result in self.results)

    @property
    def pass_rate(self) -> float:
        """返回全部案例通过率。"""

        if not self.results:
            return 0.0
        return self.passed_count / self.total_count

    @property
    def category_results(self) -> tuple[RequirementCategoryResult, ...]:
        """按稳定类别名称汇总案例数量和通过率。"""

        totals = Counter(result.category for result in self.results)
        passed = Counter(result.category for result in self.results if result.passed)
        return tuple(
            RequirementCategoryResult(
                category=category,
                total_count=totals[category],
                passed_count=passed[category],
            )
            for category in sorted(totals)
        )


def load_requirement_evaluation_suite(
    path: Path,
) -> RequirementEvaluationSuite:
    """从 UTF-8 JSON 文件加载并校验需求分析案例。"""

    raw_data = json.loads(path.read_text(encoding="utf-8"))
    return RequirementEvaluationSuite.model_validate(raw_data)


def evaluate_requirement_case(
    case: RequirementEvaluationCase,
    actual: OutfitRequirementAnalysis,
) -> RequirementCaseResult:
    """比较关键路由字段，并返回容易定位的字段差异。"""

    expected = case.expected
    mismatched_fields: list[str] = []
    for field_name in (
        "intent",
        "is_sufficient",
        "needs_wardrobe",
        "needs_weather",
        "shopping_intent",
    ):
        if getattr(actual, field_name) != getattr(
            expected,
            field_name,
        ):
            mismatched_fields.append(field_name)

    # 偏好字段属于可选评测子集：案例只有显式声明时才参与比较。
    for field_name in (
        "style_preferences",
        "color_preferences",
        "avoided_styles",
        "avoided_colors",
        "avoided_materials",
    ):
        expected_value = getattr(expected, field_name)
        if (
            expected_value is not None
            and getattr(actual, field_name) != expected_value
        ):
            mismatched_fields.append(field_name)

    if not set(expected.missing_fields_contains).issubset(
        actual.missing_fields,
    ):
        mismatched_fields.append("missing_fields_contains")

    return RequirementCaseResult(
        case_id=case.case_id,
        category=case.category,
        passed=not mismatched_fields,
        mismatched_fields=tuple(mismatched_fields),
        actual=actual,
    )


def evaluate_requirement_suite(
    suite: RequirementEvaluationSuite,
    analyze_case: Callable[
        [RequirementEvaluationCase],
        OutfitRequirementAnalysis,
    ],
) -> RequirementEvaluationReport:
    """逐条执行案例并聚合总通过率和分类通过率。"""

    return RequirementEvaluationReport(
        results=tuple(
            evaluate_requirement_case(
                case,
                analyze_case(case),
            )
            for case in suite.cases
        ),
    )


def render_requirement_baseline(
    report: RequirementEvaluationReport,
    *,
    execution_date: str,
    model_name: str,
) -> str:
    """生成不包含密钥和完整模型响应的 Markdown 基线。"""

    lines = [
        "# 结构化需求分析基线",
        "",
        "## 基线信息",
        "",
        f"- 执行日期：{execution_date}",
        f"- 模型：`{model_name}`",
        f"- 评测案例数：{report.total_count}",
        (f"- 最终结果：{report.passed_count}/{report.total_count}，通过率 {report.pass_rate:.1%}"),
        "",
        "## 分类结果",
        "",
        "| 类别 | 通过数 | 总数 | 通过率 |",
        "|---|---:|---:|---:|",
    ]
    lines.extend(
        (
            f"| {result.category} | {result.passed_count} | "
            f"{result.total_count} | {result.pass_rate:.1%} |"
        )
        for result in report.category_results
    )
    lines.extend(
        [
            "",
            "## 案例结果",
            "",
            "| case_id | 类别 | 结果 | 不匹配字段 |",
            "|---|---|---|---|",
        ],
    )
    lines.extend(
        (
            f"| {result.case_id} | {result.category} | "
            f"{'PASS' if result.passed else 'FAIL'} | "
            f"{', '.join(result.mismatched_fields) or '-'} |"
        )
        for result in report.results
    )
    lines.extend(
        [
            "",
            "## 说明",
            "",
            "该报告只保存合成案例的聚合评分和字段差异，不包含 API Key、",
            "请求头、真实用户数据或完整模型响应。",
            "",
        ],
    )
    return "\n".join(lines)
