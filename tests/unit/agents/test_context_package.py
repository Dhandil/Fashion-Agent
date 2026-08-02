"""Agent Context Package 单元测试。"""

import pytest

from app.agents.context_package import (
    ContextBudgetPolicy,
    ContextCandidate,
    ContextPriority,
    ContextProvenance,
    ContextSource,
    build_context_package,
    estimate_text_tokens,
)


def test_context_package_respects_priority_and_budget() -> None:
    """验证高优先级事实先于较长的知识片段进入上下文。"""

    package = build_context_package(
        (
            ContextCandidate(
                key="knowledge",
                source=ContextSource.KNOWLEDGE,
                priority=ContextPriority.KNOWLEDGE,
                content="知识" * 100,
            ),
            ContextCandidate(
                key="weather",
                source=ContextSource.WEATHER,
                priority=ContextPriority.CURRENT_FACT,
                content='{"condition":"阵雨"}',
                truncatable=False,
            ),
        ),
        max_chars=80,
    )

    assert package.selections[0].key == "weather"
    assert package.selections[1].key == "knowledge"
    assert package.selections[1].truncated is True
    assert package.diagnostics.selected_chars <= 80
    assert package.diagnostics.truncated_keys == ("knowledge",)


def test_context_package_deduplicates_normalised_content() -> None:
    """验证只有空白和大小写差异的重复内容不会重复注入。"""

    package = build_context_package(
        (
            ContextCandidate(
                key="explicit",
                source=ContextSource.STYLE_PROFILE,
                priority=ContextPriority.EXPLICIT_MEMORY,
                content="喜欢  简约风格",
            ),
            ContextCandidate(
                key="historical",
                source=ContextSource.OUTFIT_FEEDBACK,
                priority=ContextPriority.HISTORICAL_MEMORY,
                content="喜欢 简约风格",
            ),
        ),
        max_chars=200,
    )

    assert tuple(selection.key for selection in package.selections) == ("explicit",)
    assert package.diagnostics.duplicate_keys == ("historical",)


def test_context_package_omits_oversized_atomic_json() -> None:
    """验证不允许截断的结构化事实会整项省略。"""

    package = build_context_package(
        (
            ContextCandidate(
                key="wardrobe:0",
                source=ContextSource.WARDROBE,
                priority=ContextPriority.CURRENT_FACT,
                content='{"name":"' + "衬衫" * 100 + '"}',
                truncatable=False,
            ),
        ),
        max_chars=60,
    )

    assert package.selections == ()
    assert package.diagnostics.omitted_keys == ("wardrobe:0",)


def test_context_package_rejects_non_positive_budget() -> None:
    """验证无效预算会在装配阶段立即失败。"""

    with pytest.raises(ValueError, match="必须大于 0"):
        build_context_package((), max_chars=0)


def test_context_package_applies_independent_priority_budgets() -> None:
    """验证历史记忆和知识不能占满整个上下文预算。"""

    package = build_context_package(
        (
            ContextCandidate(
                key="current",
                source=ContextSource.REQUIREMENT_ANALYSIS,
                priority=ContextPriority.CURRENT_FACT,
                content="当前事实" * 10,
                truncatable=False,
            ),
            ContextCandidate(
                key="explicit",
                source=ContextSource.STYLE_PROFILE,
                priority=ContextPriority.EXPLICIT_MEMORY,
                content="长期档案" * 100,
            ),
            ContextCandidate(
                key="historical",
                source=ContextSource.OUTFIT_FEEDBACK,
                priority=ContextPriority.HISTORICAL_MEMORY,
                content="历史反馈" * 100,
            ),
            ContextCandidate(
                key="knowledge",
                source=ContextSource.KNOWLEDGE,
                priority=ContextPriority.KNOWLEDGE,
                content="知识内容" * 100,
            ),
        ),
        budget_policy=ContextBudgetPolicy(
            total_max_chars=500,
            explicit_memory_max_chars=100,
            historical_memory_max_chars=120,
            knowledge_max_chars=140,
        ),
    )

    usage = {item.priority: item for item in package.diagnostics.priority_usage}
    assert usage[ContextPriority.CURRENT_FACT].selected_chars == len("当前事实" * 10)
    assert usage[ContextPriority.EXPLICIT_MEMORY].selected_chars <= 100
    assert usage[ContextPriority.HISTORICAL_MEMORY].selected_chars <= 120
    assert usage[ContextPriority.KNOWLEDGE].selected_chars <= 140
    assert set(
        package.diagnostics.priority_limited_keys,
    ) == {"explicit", "historical", "knowledge"}
    assert package.diagnostics.selected_chars <= 500


def test_context_package_reports_local_token_estimates() -> None:
    """验证 Token 统计不依赖外部模型或网络 Tokenizer。"""

    package = build_context_package(
        (
            ContextCandidate(
                key="mixed",
                source=ContextSource.KNOWLEDGE,
                priority=ContextPriority.KNOWLEDGE,
                content="亚麻 breathable fabric",
            ),
        ),
        max_chars=100,
    )

    assert estimate_text_tokens("亚麻") == 2
    assert estimate_text_tokens("abcdefgh") == 2
    assert package.diagnostics.input_estimated_tokens > 0
    assert package.diagnostics.selected_estimated_tokens == package.selections[0].estimated_tokens


def test_context_budget_rejects_non_positive_category_limit() -> None:
    """验证分类预算不能通过零值隐式关闭重要上下文。"""

    with pytest.raises(
        ValueError,
        match="knowledge_max_chars",
    ):
        ContextBudgetPolicy(
            knowledge_max_chars=0,
        )


def test_context_package_preserves_provenance_when_truncated() -> None:
    """验证容量处理不会丢失知识来源、版本和更新时间。"""

    provenance = ContextProvenance(
        reference_id="knowledge-001::S01::001",
        source_path_or_url="knowledge/materials.md",
        version="2.8.0",
        updated_at="2026-07-31",
    )
    package = build_context_package(
        (
            ContextCandidate(
                key="knowledge",
                source=ContextSource.KNOWLEDGE,
                priority=ContextPriority.KNOWLEDGE,
                content="知识正文" * 30,
                provenance=(provenance,),
            ),
        ),
        max_chars=80,
    )

    assert package.selections[0].truncated is True
    assert package.selections[0].provenance == (
        provenance,
    )


def test_context_provenance_requires_traceable_source() -> None:
    """验证空来源不能伪装成可追溯元数据。"""

    with pytest.raises(ValueError, match="至少需要"):
        ContextProvenance()


def test_duplicate_content_keeps_every_provenance() -> None:
    """验证正文去重不会丢失其他命中片段的来源。"""

    first_source = ContextProvenance(
        reference_id="knowledge-001::S01::001",
    )
    second_source = ContextProvenance(
        reference_id="knowledge-002::S01::001",
    )
    package = build_context_package(
        (
            ContextCandidate(
                key="first",
                source=ContextSource.KNOWLEDGE,
                priority=ContextPriority.KNOWLEDGE,
                content="相同知识正文",
                provenance=(first_source,),
            ),
            ContextCandidate(
                key="second",
                source=ContextSource.KNOWLEDGE,
                priority=ContextPriority.KNOWLEDGE,
                content="相同知识正文",
                provenance=(second_source,),
            ),
        ),
    )

    assert len(package.selections) == 1
    assert package.selections[0].provenance == (
        first_source,
        second_source,
    )
    assert package.diagnostics.duplicate_keys == (
        "second",
    )


def test_context_package_reports_provenance_conflict() -> None:
    """验证相同来源标识的冲突版本会产生无正文诊断。"""

    package = build_context_package(
        (
            ContextCandidate(
                key="version-one",
                source=ContextSource.KNOWLEDGE,
                priority=ContextPriority.KNOWLEDGE,
                content="第一版正文",
                provenance=(
                    ContextProvenance(
                        reference_id="fragment-001",
                        version="1.0.0",
                    ),
                ),
            ),
            ContextCandidate(
                key="version-two",
                source=ContextSource.KNOWLEDGE,
                priority=ContextPriority.KNOWLEDGE,
                content="第二版正文",
                provenance=(
                    ContextProvenance(
                        reference_id="fragment-001",
                        version="2.0.0",
                    ),
                ),
            ),
        ),
    )

    assert package.diagnostics.provenance_conflict_keys == (
        "version-two",
    )
