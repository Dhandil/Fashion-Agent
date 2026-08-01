"""Agent Context Package 单元测试。"""

import pytest

from app.agents.context_package import (
    ContextCandidate,
    ContextPriority,
    ContextSource,
    build_context_package,
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
