"""当前明确要求与长期穿搭档案的确定性合并规则。"""

from collections.abc import Sequence
from dataclasses import dataclass


def _normalized_unique(
    values: Sequence[str],
) -> tuple[str, ...]:
    """保留原始表达顺序，同时按大小写去重和清理空值。"""

    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = value.strip()
        key = normalized.casefold()
        if not normalized or key in seen:
            continue
        seen.add(key)
        result.append(normalized)
    return tuple(result)


def _matches(
    value: str,
    constraint: str,
) -> bool:
    """允许“羊毛”与“羊毛混纺”等明确包含关系互相匹配。"""

    normalized_value = value.casefold()
    normalized_constraint = constraint.casefold()
    return normalized_constraint in normalized_value or normalized_value in normalized_constraint


def _without_matches(
    values: Sequence[str],
    blockers: Sequence[str],
) -> tuple[str, ...]:
    """删除与更高优先级值冲突的低优先级条目。"""

    return tuple(
        value
        for value in _normalized_unique(values)
        if not any(_matches(value, blocker) for blocker in blockers)
    )


def _merge_unique(
    *groups: Sequence[str],
) -> tuple[str, ...]:
    """按优先级顺序合并多个偏好序列。"""

    return _normalized_unique(
        tuple(value for group in groups for value in group),
    )


@dataclass(frozen=True, slots=True)
class EffectiveStyleConstraints:
    """当前请求真正生效的结构化偏好和避雷条件。"""

    preferred_styles: tuple[str, ...] = ()
    preferred_colors: tuple[str, ...] = ()
    preferred_fits: tuple[str, ...] = ()
    avoided_styles: tuple[str, ...] = ()
    avoided_colors: tuple[str, ...] = ()
    avoided_materials: tuple[str, ...] = ()

    @property
    def is_empty(self) -> bool:
        """判断当前是否没有任何可执行的偏好信息。"""

        return not any(
            (
                self.preferred_styles,
                self.preferred_colors,
                self.preferred_fits,
                self.avoided_styles,
                self.avoided_colors,
                self.avoided_materials,
            ),
        )


def resolve_style_constraints(
    *,
    current_preferred_styles: Sequence[str] = (),
    current_preferred_colors: Sequence[str] = (),
    current_avoided_styles: Sequence[str] = (),
    current_avoided_colors: Sequence[str] = (),
    current_avoided_materials: Sequence[str] = (),
    profile_preferred_styles: Sequence[str] = (),
    profile_preferred_colors: Sequence[str] = (),
    profile_preferred_fits: Sequence[str] = (),
    profile_avoided_styles: Sequence[str] = (),
    profile_avoided_colors: Sequence[str] = (),
    profile_avoided_materials: Sequence[str] = (),
) -> EffectiveStyleConstraints:
    """按“当前明确要求 > 长期档案”生成有效约束。"""

    current_avoided_styles = _normalized_unique(
        current_avoided_styles,
    )
    current_avoided_colors = _normalized_unique(
        current_avoided_colors,
    )
    current_preferred_styles = _without_matches(
        current_preferred_styles,
        current_avoided_styles,
    )
    current_preferred_colors = _without_matches(
        current_preferred_colors,
        current_avoided_colors,
    )

    return EffectiveStyleConstraints(
        preferred_styles=_merge_unique(
            current_preferred_styles,
            _without_matches(
                profile_preferred_styles,
                current_avoided_styles,
            ),
        ),
        preferred_colors=_merge_unique(
            current_preferred_colors,
            _without_matches(
                profile_preferred_colors,
                current_avoided_colors,
            ),
        ),
        preferred_fits=_normalized_unique(
            profile_preferred_fits,
        ),
        avoided_styles=_merge_unique(
            current_avoided_styles,
            _without_matches(
                profile_avoided_styles,
                current_preferred_styles,
            ),
        ),
        avoided_colors=_merge_unique(
            current_avoided_colors,
            _without_matches(
                profile_avoided_colors,
                current_preferred_colors,
            ),
        ),
        avoided_materials=_merge_unique(
            current_avoided_materials,
            profile_avoided_materials,
        ),
    )
