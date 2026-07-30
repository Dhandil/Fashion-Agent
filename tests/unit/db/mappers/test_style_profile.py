"""穿搭档案数据库转换测试。"""

from decimal import Decimal

from app.db.mappers.style_profile import (
    style_profile_entity_to_model,
    style_profile_model_to_entity,
)
from app.domain.entities.style_profile import (
    StyleProfile,
)


def test_style_profile_mapper_preserves_profile_data() -> None:
    """验证穿搭档案双向转换后数据保持一致。"""

    profile = StyleProfile(
        user_id="user-001",
        preferred_styles=(
            "简约",
            "通勤",
        ),
        preferred_colors=(
            "黑色",
            "灰色",
        ),
        avoided_colors=(
            "亮黄色",
        ),
        preferred_fits=(
            "宽松",
        ),
        avoided_materials=(
            "粗羊毛",
        ),
        common_scenarios=(
            "通勤",
            "休闲",
        ),
        typical_budget_min=Decimal("200.00"),
        typical_budget_max=Decimal("500.00"),
        notes="通勤穿搭不要过于正式",
    )

    # 模拟写入数据库前的转换
    profile_model = style_profile_entity_to_model(
        profile,
    )

    # JSON 字段应该转换为列表
    assert profile_model.preferred_styles == [
        "简约",
        "通勤",
    ]
    assert profile_model.preferred_colors == [
        "黑色",
        "灰色",
    ]
    assert profile_model.avoided_materials == [
        "粗羊毛",
    ]

    # 模拟从数据库读取后的转换
    restored_profile = style_profile_model_to_entity(
        profile_model,
    )

    # 所有领域字段应该保持一致
    assert restored_profile == profile

    # 预算继续使用 Decimal
    assert restored_profile.typical_budget_min == (
        Decimal("200.00")
    )
    assert restored_profile.typical_budget_max == (
        Decimal("500.00")
    )

    # 数据库列表应该恢复为领域元组
    assert restored_profile.common_scenarios == (
        "通勤",
        "休闲",
    )