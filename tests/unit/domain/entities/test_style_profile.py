"""用户穿搭档案领域实体测试。"""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.domain.entities.style_profile import StyleProfile


def test_style_profile_converts_preferences_to_tuples() -> None:
    """验证输入列表会转换为不可变元组。"""

    profile = StyleProfile(
        user_id="user-001",
        preferred_styles=[
            "简约",
            "通勤",
        ],
        avoided_styles=[
            "街头",
        ],
        preferred_colors=[
            "黑色",
            "灰色",
        ],
        typical_budget_min="200.00",
        typical_budget_max="500.00",
    )

    # Pydantic 应将输入列表转换为元组
    assert profile.preferred_styles == (
        "简约",
        "通勤",
    )
    assert profile.preferred_colors == (
        "黑色",
        "灰色",
    )
    assert profile.avoided_styles == (
        "街头",
    )

    # 金额字符串应该转换为 Decimal
    assert profile.typical_budget_min == Decimal(
        "200.00",
    )
    assert profile.typical_budget_max == Decimal(
        "500.00",
    )

    # 未提供的偏好应该使用空元组
    assert profile.avoided_colors == ()
    assert profile.avoided_materials == ()


def test_style_profile_is_immutable() -> None:
    """验证已经创建的档案不能被原地修改。"""

    profile = StyleProfile(
        user_id="user-001",
    )

    # frozen=True 应阻止直接修改字段
    with pytest.raises(ValidationError):
        profile.notes = "用户不喜欢高领"


def test_style_profile_rejects_invalid_budget_range() -> None:
    """验证最低预算不能高于最高预算。"""

    with pytest.raises(
        ValidationError,
        match="最低预算不能高于最高预算",
    ):
        StyleProfile(
            user_id="user-001",
            typical_budget_min="600.00",
            typical_budget_max="300.00",
        )


def test_style_profile_normalizes_preference_values() -> None:
    """验证偏好值会去除空白、空项和大小写重复项。"""

    profile = StyleProfile(
        user_id="user-001",
        preferred_styles=(
            " 简约 ",
            "简约",
            "CASUAL",
            " casual ",
            "",
            "   ",
        ),
    )

    assert profile.preferred_styles == (
        "简约",
        "CASUAL",
    )


@pytest.mark.parametrize(
    (
        "preferred_field",
        "avoided_field",
        "error_message",
    ),
    (
        (
            "preferred_styles",
            "avoided_styles",
            "同一风格不能同时标记为喜欢和避免",
        ),
        (
            "preferred_colors",
            "avoided_colors",
            "同一颜色不能同时标记为喜欢和避免",
        ),
    ),
)
def test_style_profile_rejects_conflicting_preferences(
    preferred_field: str,
    avoided_field: str,
    error_message: str,
) -> None:
    """验证同一偏好不能同时存在于喜欢和避免列表。"""

    profile_data: dict[str, object] = {
        "user_id": "user-001",
        preferred_field: (
            " 浅蓝色 ",
        ),
        avoided_field: (
            "浅蓝色",
        ),
    }

    with pytest.raises(
        ValidationError,
        match=error_message,
    ):
        StyleProfile.model_validate(
            profile_data,
        )


def test_style_profile_can_create_updated_version() -> None:
    """验证可以根据旧档案创建经过校验的新版本。"""

    original_profile = StyleProfile(
        user_id="user-001",
        preferred_styles=("简约",),
    )

    # 将旧档案转换成可用于重新校验的数据
    updated_data = original_profile.model_dump()

    # 加入用户新确认的长期说明
    updated_data["notes"] = "通勤穿搭不要过于正式"

    # 创建新的档案版本，而不是修改旧对象
    updated_profile = StyleProfile.model_validate(
        updated_data,
    )

    # 旧档案保持不变
    assert original_profile.notes is None

    # 新档案包含用户刚刚确认的说明
    assert updated_profile.notes == (
        "通勤穿搭不要过于正式"
    )
