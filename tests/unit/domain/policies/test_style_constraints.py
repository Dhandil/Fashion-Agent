"""当前要求与长期档案优先级合并测试。"""

from app.domain.policies.style_constraints import (
    resolve_style_constraints,
)


def test_current_preferences_override_profile_avoidances() -> None:
    """验证本轮主动选择可以覆盖长期避免项。"""

    constraints = resolve_style_constraints(
        current_preferred_styles=("街头风",),
        current_preferred_colors=("黑色",),
        profile_avoided_styles=("街头",),
        profile_avoided_colors=("黑色",),
    )

    assert constraints.preferred_styles == ("街头风",)
    assert constraints.preferred_colors == ("黑色",)
    assert constraints.avoided_styles == ()
    assert constraints.avoided_colors == ()


def test_current_avoidances_override_positive_preferences() -> None:
    """验证本轮明确避免项会覆盖同轮和长期正向偏好。"""

    constraints = resolve_style_constraints(
        current_preferred_styles=("简约",),
        current_preferred_colors=("黑色",),
        current_avoided_styles=("简约",),
        current_avoided_colors=("黑色",),
        profile_preferred_styles=("简约", "休闲"),
        profile_preferred_colors=("黑色", "米白"),
    )

    assert constraints.preferred_styles == ("休闲",)
    assert constraints.preferred_colors == ("米白",)
    assert constraints.avoided_styles == ("简约",)
    assert constraints.avoided_colors == ("黑色",)


def test_profile_constraints_apply_without_current_override() -> None:
    """验证本轮没有冲突表达时长期偏好继续生效。"""

    constraints = resolve_style_constraints(
        profile_preferred_styles=("简约",),
        profile_preferred_fits=("宽松",),
        profile_avoided_colors=("荧光色",),
        profile_avoided_materials=("粗糙羊毛",),
    )

    assert constraints.preferred_styles == ("简约",)
    assert constraints.preferred_fits == ("宽松",)
    assert constraints.avoided_colors == ("荧光色",)
    assert constraints.avoided_materials == ("粗糙羊毛",)
