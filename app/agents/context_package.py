"""Agent 上下文预算、优先级与去重模型。"""

from dataclasses import dataclass
from enum import IntEnum, StrEnum

DEFAULT_CONTEXT_MAX_CHARS = 12_000
_TRUNCATION_MARKER = "\n[上下文已按预算截断]"
_MIN_TRUNCATED_CONTENT_CHARS = 32


class ContextPriority(IntEnum):
    """上下文优先级；数值越小越先进入模型上下文。"""

    CURRENT_FACT = 10
    EXPLICIT_MEMORY = 20
    HISTORICAL_MEMORY = 30
    KNOWLEDGE = 40


class ContextSource(StrEnum):
    """可进入 Agent 上下文的数据来源。"""

    WEATHER = "weather"
    WEATHER_TOOL = "weather_tool"
    WEATHER_GUIDANCE = "weather_guidance"
    WARDROBE = "wardrobe"
    PRODUCTS = "products"
    REQUIREMENT_ANALYSIS = "requirement_analysis"
    EFFECTIVE_STYLE_CONSTRAINTS = "effective_style_constraints"
    STYLE_PROFILE = "style_profile"
    PREVIOUS_OUTFIT = "previous_outfit"
    OUTFIT_FEEDBACK = "outfit_feedback"
    RECENT_OUTFITS = "recent_outfits"
    KNOWLEDGE = "knowledge"


@dataclass(frozen=True, slots=True)
class ContextCandidate:
    """进入预算计算前的一项候选上下文。"""

    key: str
    source: ContextSource
    priority: ContextPriority
    content: str
    truncatable: bool = True


@dataclass(frozen=True, slots=True)
class ContextSelection:
    """预算处理后保留下来的一项上下文。"""

    key: str
    source: ContextSource
    content: str
    original_chars: int
    truncated: bool = False


@dataclass(frozen=True, slots=True)
class ContextPackageDiagnostics:
    """不包含正文的上下文装配诊断信息。"""

    max_chars: int
    input_items: int
    input_chars: int
    selected_items: int
    selected_chars: int
    duplicate_keys: tuple[str, ...]
    omitted_keys: tuple[str, ...]
    truncated_keys: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ContextPackage:
    """一次模型调用实际选中的上下文及其诊断。"""

    selections: tuple[ContextSelection, ...]
    diagnostics: ContextPackageDiagnostics

    def contents_for(
        self,
        source: ContextSource,
    ) -> tuple[str, ...]:
        """按选中顺序返回指定来源的全部正文。"""

        return tuple(
            selection.content for selection in self.selections if selection.source is source
        )

    def combined_content_for(
        self,
        source: ContextSource,
        separator: str = "\n",
    ) -> str:
        """合并指定来源的正文，便于写入提示词或 JSON。"""

        return separator.join(self.contents_for(source))


def _normalise_for_deduplication(content: str) -> str:
    """统一空白和大小写，识别内容完全相同的上下文。"""

    return " ".join(content.split()).casefold()


def build_context_package(
    candidates: tuple[ContextCandidate, ...],
    max_chars: int = DEFAULT_CONTEXT_MAX_CHARS,
) -> ContextPackage:
    """按优先级对候选上下文执行去重、预算分配与安全截断。"""

    if max_chars <= 0:
        raise ValueError("max_chars 必须大于 0")

    # 相同优先级保持调用方提供的顺序，确保结果可复现。
    ordered_candidates = sorted(
        enumerate(candidates),
        key=lambda item: (
            item[1].priority,
            item[0],
        ),
    )
    selections: list[ContextSelection] = []
    duplicate_keys: list[str] = []
    omitted_keys: list[str] = []
    truncated_keys: list[str] = []
    seen_content: set[str] = set()
    selected_chars = 0
    input_chars = 0
    input_items = 0

    for _, candidate in ordered_candidates:
        content = candidate.content.strip()
        if not content:
            continue

        input_items += 1
        input_chars += len(content)
        deduplication_key = _normalise_for_deduplication(
            content,
        )
        if deduplication_key in seen_content:
            duplicate_keys.append(candidate.key)
            continue
        seen_content.add(deduplication_key)

        remaining_chars = max_chars - selected_chars
        if len(content) <= remaining_chars:
            selections.append(
                ContextSelection(
                    key=candidate.key,
                    source=candidate.source,
                    content=content,
                    original_chars=len(content),
                ),
            )
            selected_chars += len(content)
            continue

        usable_chars = remaining_chars - len(
            _TRUNCATION_MARKER,
        )
        if candidate.truncatable and usable_chars >= _MIN_TRUNCATED_CONTENT_CHARS:
            truncated_content = content[:usable_chars].rstrip() + _TRUNCATION_MARKER
            selections.append(
                ContextSelection(
                    key=candidate.key,
                    source=candidate.source,
                    content=truncated_content,
                    original_chars=len(content),
                    truncated=True,
                ),
            )
            selected_chars += len(truncated_content)
            truncated_keys.append(candidate.key)
            continue

        omitted_keys.append(candidate.key)

    diagnostics = ContextPackageDiagnostics(
        max_chars=max_chars,
        input_items=input_items,
        input_chars=input_chars,
        selected_items=len(selections),
        selected_chars=selected_chars,
        duplicate_keys=tuple(duplicate_keys),
        omitted_keys=tuple(omitted_keys),
        truncated_keys=tuple(truncated_keys),
    )
    return ContextPackage(
        selections=tuple(selections),
        diagnostics=diagnostics,
    )
