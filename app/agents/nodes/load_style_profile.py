"""加载用户长期穿搭档案的个性化上下文节点。"""

from collections.abc import Awaitable, Callable

from app.agents.schemas.style_profile import (
    StyleProfileSnapshot,
)
from app.agents.state.shopping import ShoppingAgentState
from app.domain.entities.style_profile import StyleProfile
from app.domain.repositories.style_profile import (
    StyleProfileRepository,
)


def build_style_profile_context(
    profile: StyleProfile,
) -> str:
    """把 Style Profile 转换成不包含用户 ID 的模型上下文。"""

    context_records: list[str] = []
    sequence_fields = (
        (
            "喜欢的风格",
            profile.preferred_styles,
        ),
        (
            "希望避免的风格",
            profile.avoided_styles,
        ),
        (
            "喜欢的颜色",
            profile.preferred_colors,
        ),
        (
            "希望避免的颜色",
            profile.avoided_colors,
        ),
        (
            "喜欢的版型",
            profile.preferred_fits,
        ),
        (
            "希望避免的材质",
            profile.avoided_materials,
        ),
        (
            "常见穿搭场景",
            profile.common_scenarios,
        ),
    )

    for label, values in sequence_fields:
        if values:
            context_records.append(
                f"- {label}：{'、'.join(values)}",
            )

    if profile.typical_budget_min is not None or profile.typical_budget_max is not None:
        minimum = (
            str(profile.typical_budget_min) if profile.typical_budget_min is not None else "未设置"
        )
        maximum = (
            str(profile.typical_budget_max) if profile.typical_budget_max is not None else "未设置"
        )
        context_records.append(
            f"- 常用预算范围：{minimum} 至 {maximum} 元",
        )

    if profile.notes:
        context_records.append(
            f"- 用户主动说明：{profile.notes}",
        )

    return "\n".join(context_records)


def create_load_style_profile_node(
    repository: StyleProfileRepository,
    user_id: str,
) -> Callable[
    [ShoppingAgentState],
    Awaitable[
        dict[
            str,
            str | StyleProfileSnapshot | None,
        ]
    ],
]:
    """创建绑定当前用户与请求级档案仓库的加载节点。"""

    async def load_style_profile(
        _state: ShoppingAgentState,
    ) -> dict[
        str,
        str | StyleProfileSnapshot | None,
    ]:
        """读取当前 Style Profile 并覆盖旧的档案上下文。"""

        profile = await repository.get_by_user_id(
            user_id,
        )

        return {
            "style_profile_context": (
                build_style_profile_context(profile) if profile is not None else ""
            ),
            "style_profile_snapshot": (
                StyleProfileSnapshot.from_profile(profile) if profile is not None else None
            ),
        }

    return load_style_profile
