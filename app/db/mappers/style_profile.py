"""穿搭档案数据库模型与领域实体转换。"""

from app.db.models.style_profile import (
    StyleProfileModel,
)
from app.domain.entities.style_profile import (
    StyleProfile,
)


def style_profile_entity_to_model(
    profile: StyleProfile,
) -> StyleProfileModel:
    """将穿搭档案领域实体转换为数据库模型。"""

    return StyleProfileModel(
        user_id=profile.user_id,
        # 领域层使用元组，数据库 JSON 字段使用列表
        preferred_styles=list(
            profile.preferred_styles,
        ),
        preferred_colors=list(
            profile.preferred_colors,
        ),
        avoided_colors=list(
            profile.avoided_colors,
        ),
        preferred_fits=list(
            profile.preferred_fits,
        ),
        avoided_materials=list(
            profile.avoided_materials,
        ),
        common_scenarios=list(
            profile.common_scenarios,
        ),
        typical_budget_min=(profile.typical_budget_min),
        typical_budget_max=(profile.typical_budget_max),
        notes=profile.notes,
    )


def style_profile_model_to_entity(
    profile_model: StyleProfileModel,
) -> StyleProfile:
    """将穿搭档案数据库模型转换为领域实体。"""

    return StyleProfile(
        user_id=profile_model.user_id,
        # 显式恢复成领域层使用的只读元组
        preferred_styles=tuple(
            profile_model.preferred_styles,
        ),
        preferred_colors=tuple(
            profile_model.preferred_colors,
        ),
        avoided_colors=tuple(
            profile_model.avoided_colors,
        ),
        preferred_fits=tuple(
            profile_model.preferred_fits,
        ),
        avoided_materials=tuple(
            profile_model.avoided_materials,
        ),
        common_scenarios=tuple(
            profile_model.common_scenarios,
        ),
        typical_budget_min=(profile_model.typical_budget_min),
        typical_budget_max=(profile_model.typical_budget_max),
        notes=profile_model.notes,
    )
