"""穿搭方案数据库模型测试。"""

from sqlalchemy import (
    CheckConstraint,
    ForeignKeyConstraint,
)

from app.db.models.outfit import (
    OutfitItemModel,
    OutfitModel,
)


def test_outfit_models_define_required_columns() -> None:
    """验证穿搭主表和穿搭单品表包含必要字段。"""

    outfit_table = OutfitModel.__table__
    item_table = OutfitItemModel.__table__

    assert outfit_table.name == "outfits"
    assert set(outfit_table.columns.keys()) == {
        "user_id",
        "outfit_id",
        "name",
        "scenario",
        "style_tags",
        "season",
        "recommendation_reason",
        "notes",
        "is_favorite",
        "created_at",
        "updated_at",
    }

    assert item_table.name == "outfit_items"
    assert set(item_table.columns.keys()) == {
        "user_id",
        "outfit_id",
        "position",
        "role",
        "name",
        "source",
        "source_reference_id",
        "reason",
    }


def test_outfit_models_use_composite_primary_keys() -> None:
    """验证穿搭表和单品表使用正确的复合主键。"""

    outfit_table = OutfitModel.__table__
    item_table = OutfitItemModel.__table__

    assert list(
        outfit_table.primary_key.columns.keys(),
    ) == [
        "user_id",
        "outfit_id",
    ]

    assert list(
        item_table.primary_key.columns.keys(),
    ) == [
        "user_id",
        "outfit_id",
        "position",
    ]


def test_outfit_item_model_defines_parent_foreign_key() -> None:
    """验证穿搭单品通过级联外键关联穿搭主表。"""

    item_table = OutfitItemModel.__table__

    # 从表约束中找出复合外键
    foreign_keys = [
        constraint
        for constraint in item_table.constraints
        if isinstance(
            constraint,
            ForeignKeyConstraint,
        )
    ]

    assert len(foreign_keys) == 1

    outfit_foreign_key = foreign_keys[0]

    assert (
        outfit_foreign_key.name
        == "fk_outfit_items_outfit"
    )
    assert outfit_foreign_key.ondelete == "CASCADE"

    # 外键应该同时包含用户 ID 和穿搭 ID
    assert list(
        outfit_foreign_key.columns.keys(),
    ) == [
        "user_id",
        "outfit_id",
    ]


def test_outfit_models_define_constraints_and_indexes() -> None:
    """验证单品来源约束以及穿搭查询索引。"""

    outfit_table = OutfitModel.__table__
    item_table = OutfitItemModel.__table__

    # 收集穿搭单品表的检查约束名称
    check_constraint_names = {
        constraint.name
        for constraint in item_table.constraints
        if isinstance(
            constraint,
            CheckConstraint,
        )
    }

    assert check_constraint_names == {
        "ck_outfit_items_source",
        "ck_outfit_items_source_reference",
    }

    # 收集穿搭主表的索引名称
    index_names = {
        index.name
        for index in outfit_table.indexes
    }

    assert index_names == {
        "ix_outfits_user_scenario",
        "ix_outfits_user_favorite",
    }