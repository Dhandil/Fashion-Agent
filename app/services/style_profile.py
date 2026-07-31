"""用户长期穿搭档案应用服务。"""

from decimal import Decimal

from app.domain.entities.style_profile import StyleProfile
from app.domain.repositories.style_profile import (
    StyleProfileRepository,
)


async def get_style_profile(
    repository: StyleProfileRepository,
    user_id: str,
) -> StyleProfile:
    """读取当前用户档案；不存在时返回未持久化的空档案。"""

    profile = await repository.get_by_user_id(
        user_id,
    )

    if profile is not None:
        return profile

    return StyleProfile(
        user_id=user_id,
    )


async def replace_style_profile(
    repository: StyleProfileRepository,
    user_id: str,
    preferred_styles: tuple[str, ...] = (),
    preferred_colors: tuple[str, ...] = (),
    avoided_colors: tuple[str, ...] = (),
    preferred_fits: tuple[str, ...] = (),
    avoided_materials: tuple[str, ...] = (),
    common_scenarios: tuple[str, ...] = (),
    typical_budget_min: Decimal | None = None,
    typical_budget_max: Decimal | None = None,
    notes: str | None = None,
) -> StyleProfile:
    """用用户明确提交的内容完整替换长期穿搭档案。"""

    profile = StyleProfile(
        user_id=user_id,
        preferred_styles=preferred_styles,
        preferred_colors=preferred_colors,
        avoided_colors=avoided_colors,
        preferred_fits=preferred_fits,
        avoided_materials=avoided_materials,
        common_scenarios=common_scenarios,
        typical_budget_min=typical_budget_min,
        typical_budget_max=typical_budget_max,
        notes=notes,
    )

    return await repository.save(
        profile,
    )
