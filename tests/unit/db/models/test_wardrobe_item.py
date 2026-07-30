"""衣橱单品数据库模型测试。"""

from sqlalchemy import CheckConstraint

from app.db.models.wardrobe_item import (
    WardrobeItemModel,
)


def test_wardrobe_item_model_defines_required_columns() -> None:
    """验证衣橱表包含全部必要字段。"""

    wardrobe_table = WardrobeItemModel.__table__

    assert wardrobe_table.name == "wardrobe_items"

    assert set(wardrobe_table.columns.keys()) == {
        "user_id",
        "wardrobe_item_id",
        "name",
        "category",
        "brand",
        "colors",
        "materials",
        "size",
        "style_tags",
        "seasons",
        "scenarios",
        "image_url",
        "status",
        "notes",
        "created_at",
        "updated_at",
    }


def test_wardrobe_item_model_uses_composite_primary_key() -> None:
    """验证用户 ID 和单品 ID 共同组成主键。"""

    wardrobe_table = WardrobeItemModel.__table__

    primary_key_columns = list(
        wardrobe_table.primary_key.columns.keys(),
    )

    assert primary_key_columns == [
        "user_id",
        "wardrobe_item_id",
    ]


def test_wardrobe_item_model_defines_constraints_and_indexes() -> None:
    """验证衣物状态约束和常用查询索引。"""

    wardrobe_table = WardrobeItemModel.__table__

    # 收集所有数据库检查约束名称
    check_constraint_names = {
        constraint.name
        for constraint in wardrobe_table.constraints
        if isinstance(
            constraint,
            CheckConstraint,
        )
    }

    assert (
        "ck_wardrobe_items_status"
        in check_constraint_names
    )

    # 收集所有显式索引名称
    index_names = {
        index.name
        for index in wardrobe_table.indexes
    }

    assert index_names == {
        "ix_wardrobe_items_user_status",
        "ix_wardrobe_items_user_category",
    }