"""Agent 上下文预算、优先级与去重模型。"""

from collections.abc import Mapping
from dataclasses import dataclass, replace
from enum import IntEnum, StrEnum
from math import ceil

DEFAULT_CONTEXT_MAX_CHARS = 12_000
DEFAULT_EXPLICIT_MEMORY_MAX_CHARS = 3_000
DEFAULT_HISTORICAL_MEMORY_MAX_CHARS = 3_000
DEFAULT_KNOWLEDGE_MAX_CHARS = 4_000
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
    CONVERSATION_SUMMARY = "conversation_summary"
    OUTFIT_FEEDBACK = "outfit_feedback"
    RECENT_OUTFITS = "recent_outfits"
    KNOWLEDGE = "knowledge"


@dataclass(frozen=True, slots=True)
class ContextBudgetPolicy:
    """单次模型调用的总预算和分类预算。"""

    total_max_chars: int = DEFAULT_CONTEXT_MAX_CHARS
    explicit_memory_max_chars: int = DEFAULT_EXPLICIT_MEMORY_MAX_CHARS
    historical_memory_max_chars: int = DEFAULT_HISTORICAL_MEMORY_MAX_CHARS
    knowledge_max_chars: int = DEFAULT_KNOWLEDGE_MAX_CHARS

    def __post_init__(self) -> None:
        """预算必须是可执行的正数。"""

        if self.total_max_chars <= 0:
            raise ValueError("total_max_chars 必须大于 0")
        for field_name, value in (
            (
                "explicit_memory_max_chars",
                self.explicit_memory_max_chars,
            ),
            (
                "historical_memory_max_chars",
                self.historical_memory_max_chars,
            ),
            (
                "knowledge_max_chars",
                self.knowledge_max_chars,
            ),
        ):
            if value <= 0:
                raise ValueError(f"{field_name} 必须大于 0")

    def priority_limits(
        self,
    ) -> Mapping[ContextPriority, int]:
        """返回需要独立限制的上下文类别。"""

        return {
            ContextPriority.EXPLICIT_MEMORY: (self.explicit_memory_max_chars),
            ContextPriority.HISTORICAL_MEMORY: (self.historical_memory_max_chars),
            ContextPriority.KNOWLEDGE: self.knowledge_max_chars,
        }


DEFAULT_CONTEXT_BUDGET_POLICY = ContextBudgetPolicy()


@dataclass(frozen=True, slots=True)
class ContextProvenance:
    """一项上下文的结构化来源信息，不包含正文。"""

    reference_id: str | None = None
    source_path_or_url: str | None = None
    version: str | None = None
    updated_at: str | None = None

    def __post_init__(self) -> None:
        """来源至少需要稳定标识或可追溯路径。"""

        has_reference = bool(
            self.reference_id and self.reference_id.strip(),
        )
        has_source_path = bool(
            self.source_path_or_url
            and self.source_path_or_url.strip(),
        )
        if not has_reference and not has_source_path:
            raise ValueError(
                "ContextProvenance 至少需要 reference_id 或 source_path_or_url",
            )


@dataclass(frozen=True, slots=True)
class ContextCandidate:
    """进入预算计算前的一项候选上下文。"""

    key: str
    source: ContextSource
    priority: ContextPriority
    content: str
    truncatable: bool = True
    provenance: tuple[ContextProvenance, ...] = ()


@dataclass(frozen=True, slots=True)
class ContextSelection:
    """预算处理后保留下来的一项上下文。"""

    key: str
    source: ContextSource
    content: str
    original_chars: int
    estimated_tokens: int
    truncated: bool = False
    provenance: tuple[ContextProvenance, ...] = ()


@dataclass(frozen=True, slots=True)
class ContextPriorityUsage:
    """不包含正文的单类上下文预算使用量。"""

    priority: ContextPriority
    max_chars: int | None
    selected_items: int
    selected_chars: int
    estimated_tokens: int


@dataclass(frozen=True, slots=True)
class ContextPackageDiagnostics:
    """不包含正文的上下文装配诊断信息。"""

    max_chars: int
    input_items: int
    input_chars: int
    input_estimated_tokens: int
    selected_items: int
    selected_chars: int
    selected_estimated_tokens: int
    duplicate_keys: tuple[str, ...]
    omitted_keys: tuple[str, ...]
    truncated_keys: tuple[str, ...]
    priority_limited_keys: tuple[str, ...]
    provenance_conflict_keys: tuple[str, ...]
    priority_usage: tuple[ContextPriorityUsage, ...]


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


def _provenance_identity(
    provenance: ContextProvenance,
) -> str:
    """返回来源冲突检测使用的稳定身份。"""

    return (
        provenance.reference_id
        or provenance.source_path_or_url
        or ""
    ).casefold()


def _provenance_conflicts(
    existing: ContextProvenance,
    current: ContextProvenance,
) -> bool:
    """判断同一来源的已知元数据是否互相矛盾。"""

    return any(
        existing_value is not None
        and current_value is not None
        and existing_value != current_value
        for existing_value, current_value in (
            (
                existing.source_path_or_url,
                current.source_path_or_url,
            ),
            (existing.version, current.version),
            (existing.updated_at, current.updated_at),
        )
    )


def _merge_provenance(
    *groups: tuple[ContextProvenance, ...],
) -> tuple[ContextProvenance, ...]:
    """按出现顺序合并完全相同的来源记录。"""

    merged: list[ContextProvenance] = []
    for provenance in (
        item for group in groups for item in group
    ):
        if provenance not in merged:
            merged.append(provenance)
    return tuple(merged)


def estimate_text_tokens(content: str) -> int:
    """用稳定本地规则近似估算中英文混合文本 Token 数。"""

    estimated_tokens = 0
    ascii_run_length = 0

    def flush_ascii_run() -> None:
        nonlocal ascii_run_length, estimated_tokens
        if ascii_run_length:
            estimated_tokens += ceil(ascii_run_length / 4)
            ascii_run_length = 0

    for character in content:
        if character.isascii() and (character.isalnum() or character in {"_", "-"}):
            ascii_run_length += 1
            continue

        flush_ascii_run()
        if not character.isspace():
            # 中文字符及标点按一个 Token 保守估算。
            estimated_tokens += 1

    flush_ascii_run()
    return estimated_tokens


def _resolve_budget_policy(
    *,
    max_chars: int | None,
    budget_policy: ContextBudgetPolicy | None,
) -> ContextBudgetPolicy:
    """兼容旧的单一总字符预算调用方式。"""

    if max_chars is not None and budget_policy is not None:
        raise ValueError(
            "max_chars 和 budget_policy 不能同时提供",
        )
    if budget_policy is not None:
        return budget_policy
    if max_chars is None:
        return ContextBudgetPolicy()
    return ContextBudgetPolicy(
        total_max_chars=max_chars,
        explicit_memory_max_chars=max_chars,
        historical_memory_max_chars=max_chars,
        knowledge_max_chars=max_chars,
    )


def build_context_package(
    candidates: tuple[ContextCandidate, ...],
    max_chars: int | None = None,
    *,
    budget_policy: ContextBudgetPolicy | None = None,
) -> ContextPackage:
    """按优先级对候选上下文执行去重、预算分配与安全截断。"""

    policy = _resolve_budget_policy(
        max_chars=max_chars,
        budget_policy=budget_policy,
    )
    max_chars = policy.total_max_chars
    priority_limits = policy.priority_limits()

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
    priority_limited_keys: list[str] = []
    provenance_conflict_keys: list[str] = []
    seen_content: set[str] = set()
    selected_content_indexes: dict[str, int] = {}
    seen_provenance: dict[str, ContextProvenance] = {}
    selected_chars = 0
    selected_estimated_tokens = 0
    input_chars = 0
    input_estimated_tokens = 0
    input_items = 0
    priority_selected_chars = {priority: 0 for priority in ContextPriority}
    priority_selected_items = {priority: 0 for priority in ContextPriority}
    priority_estimated_tokens = {priority: 0 for priority in ContextPriority}

    for _, candidate in ordered_candidates:
        content = candidate.content.strip()
        if not content:
            continue

        input_items += 1
        input_chars += len(content)
        input_estimated_tokens += estimate_text_tokens(
            content,
        )
        has_provenance_conflict = False
        for provenance in candidate.provenance:
            identity = _provenance_identity(provenance)
            existing_provenance = seen_provenance.get(
                identity,
            )
            if existing_provenance is None:
                seen_provenance[identity] = provenance
            elif _provenance_conflicts(
                existing_provenance,
                provenance,
            ):
                has_provenance_conflict = True
        if has_provenance_conflict:
            provenance_conflict_keys.append(candidate.key)

        deduplication_key = _normalise_for_deduplication(
            content,
        )
        if deduplication_key in seen_content:
            duplicate_keys.append(candidate.key)
            selected_index = selected_content_indexes.get(
                deduplication_key,
            )
            if selected_index is not None:
                selected = selections[selected_index]
                selections[selected_index] = replace(
                    selected,
                    provenance=_merge_provenance(
                        selected.provenance,
                        candidate.provenance,
                    ),
                )
            continue
        seen_content.add(deduplication_key)

        total_remaining_chars = max_chars - selected_chars
        priority_limit = priority_limits.get(
            candidate.priority,
        )
        priority_remaining_chars = (
            priority_limit - priority_selected_chars[candidate.priority]
            if priority_limit is not None
            else total_remaining_chars
        )
        remaining_chars = min(
            total_remaining_chars,
            priority_remaining_chars,
        )
        limited_by_priority = (
            priority_limit is not None
            and priority_remaining_chars <= total_remaining_chars
            and len(content) > priority_remaining_chars
        )
        if limited_by_priority:
            priority_limited_keys.append(candidate.key)

        if len(content) <= remaining_chars:
            estimated_tokens = estimate_text_tokens(
                content,
            )
            selections.append(
                ContextSelection(
                    key=candidate.key,
                    source=candidate.source,
                    content=content,
                    original_chars=len(content),
                    estimated_tokens=estimated_tokens,
                    provenance=candidate.provenance,
                ),
            )
            selected_content_indexes[deduplication_key] = (
                len(selections) - 1
            )
            selected_chars += len(content)
            selected_estimated_tokens += estimated_tokens
            priority_selected_chars[candidate.priority] += len(
                content,
            )
            priority_selected_items[candidate.priority] += 1
            priority_estimated_tokens[candidate.priority] += estimated_tokens
            continue

        usable_chars = remaining_chars - len(
            _TRUNCATION_MARKER,
        )
        if candidate.truncatable and usable_chars >= _MIN_TRUNCATED_CONTENT_CHARS:
            truncated_content = content[:usable_chars].rstrip() + _TRUNCATION_MARKER
            estimated_tokens = estimate_text_tokens(
                truncated_content,
            )
            selections.append(
                ContextSelection(
                    key=candidate.key,
                    source=candidate.source,
                    content=truncated_content,
                    original_chars=len(content),
                    estimated_tokens=estimated_tokens,
                    truncated=True,
                    provenance=candidate.provenance,
                ),
            )
            selected_content_indexes[deduplication_key] = (
                len(selections) - 1
            )
            selected_chars += len(truncated_content)
            selected_estimated_tokens += estimated_tokens
            priority_selected_chars[candidate.priority] += len(truncated_content)
            priority_selected_items[candidate.priority] += 1
            priority_estimated_tokens[candidate.priority] += estimated_tokens
            truncated_keys.append(candidate.key)
            continue

        omitted_keys.append(candidate.key)

    diagnostics = ContextPackageDiagnostics(
        max_chars=max_chars,
        input_items=input_items,
        input_chars=input_chars,
        input_estimated_tokens=input_estimated_tokens,
        selected_items=len(selections),
        selected_chars=selected_chars,
        selected_estimated_tokens=(selected_estimated_tokens),
        duplicate_keys=tuple(duplicate_keys),
        omitted_keys=tuple(omitted_keys),
        truncated_keys=tuple(truncated_keys),
        priority_limited_keys=tuple(
            priority_limited_keys,
        ),
        provenance_conflict_keys=tuple(
            provenance_conflict_keys,
        ),
        priority_usage=tuple(
            ContextPriorityUsage(
                priority=priority,
                max_chars=priority_limits.get(priority),
                selected_items=(priority_selected_items[priority]),
                selected_chars=(priority_selected_chars[priority]),
                estimated_tokens=(priority_estimated_tokens[priority]),
            )
            for priority in ContextPriority
        ),
    )
    return ContextPackage(
        selections=tuple(selections),
        diagnostics=diagnostics,
    )
