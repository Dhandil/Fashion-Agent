"""从 Agent State 计算本轮有效穿搭约束。"""

import json
from dataclasses import asdict

from app.agents.state.shopping import ShoppingAgentState
from app.domain.policies.style_constraints import (
    EffectiveStyleConstraints,
    resolve_style_constraints,
)


def get_effective_style_constraints(
    state: ShoppingAgentState,
) -> EffectiveStyleConstraints:
    """读取当前需求和长期快照，生成唯一有效约束。"""

    analysis = state.get("requirement_analysis")
    profile = state.get("style_profile_snapshot")

    return resolve_style_constraints(
        current_preferred_styles=(analysis.style_preferences if analysis is not None else ()),
        current_preferred_colors=(analysis.color_preferences if analysis is not None else ()),
        current_avoided_styles=(analysis.avoided_styles if analysis is not None else ()),
        current_avoided_colors=(analysis.avoided_colors if analysis is not None else ()),
        current_avoided_materials=(analysis.avoided_materials if analysis is not None else ()),
        profile_preferred_styles=(profile.preferred_styles if profile is not None else ()),
        profile_preferred_colors=(profile.preferred_colors if profile is not None else ()),
        profile_preferred_fits=(profile.preferred_fits if profile is not None else ()),
        profile_avoided_styles=(profile.avoided_styles if profile is not None else ()),
        profile_avoided_colors=(profile.avoided_colors if profile is not None else ()),
        profile_avoided_materials=(profile.avoided_materials if profile is not None else ()),
    )


def serialize_style_constraints(
    constraints: EffectiveStyleConstraints,
) -> str:
    """把有效约束转换成不含用户标识的稳定 JSON。"""

    return json.dumps(
        asdict(constraints),
        ensure_ascii=False,
        sort_keys=True,
    )
