"""用户穿搭档案数据库模型测试。"""

from sqlalchemy import CheckConstraint, Numeric

from app.db.models.style_profile import (
    StyleProfileModel,
)


def test_style_profile_model_defines_required_columns() -> None:
    """验证穿搭档案表包含全部必要字段。"""

    profile_table = StyleProfileModel.__table__

    assert profile_table.name == "style_profiles"

    column_names = set(
        profile_table.columns.keys(),
    )

    assert column_names == {
        "user_id",
        "preferred_styles",
        "preferred_colors",
        "avoided_colors",
        "preferred_fits",
        "avoided_materials",
        "common_scenarios",
        "typical_budget_min",
        "typical_budget_max",
        "notes",
        "created_at",
        "updated_at",
    }

    # 每个用户只能拥有一份当前穿搭档案
    assert list(
        profile_table.primary_key.columns.keys(),
    ) == [
        "user_id",
    ]


def test_style_profile_model_defines_budget_constraint() -> None:
    """验证数据库层具有预算范围保护。"""

    profile_table = StyleProfileModel.__table__

    # 找出表中定义的 CheckConstraint
    check_constraints = [
        constraint
        for constraint in profile_table.constraints
        if isinstance(
            constraint,
            CheckConstraint,
        )
    ]

    constraint_names = {
        constraint.name
        for constraint in check_constraints
    }

    assert (
        "ck_style_profiles_budget_range"
        in constraint_names
    )

    # 两个预算字段都应该使用定点数
    minimum_budget_type = profile_table.columns[
        "typical_budget_min"
    ].type
    maximum_budget_type = profile_table.columns[
        "typical_budget_max"
    ].type

    assert isinstance(
        minimum_budget_type,
        Numeric,
    )
    assert isinstance(
        maximum_budget_type,
        Numeric,
    )
    assert minimum_budget_type.precision == 12
    assert minimum_budget_type.scale == 2