"""用户长期穿搭档案加载节点测试。"""

from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from app.agents.nodes.load_style_profile import (
    build_style_profile_context,
    create_load_style_profile_node,
)
from app.domain.entities.style_profile import StyleProfile
from app.domain.repositories.style_profile import (
    StyleProfileRepository,
)


def create_style_profile() -> StyleProfile:
    """创建包含多类长期偏好的测试档案。"""

    return StyleProfile(
        user_id="user-001",
        preferred_styles=(
            "简约",
            "休闲",
        ),
        avoided_styles=(
            "街头",
        ),
        preferred_colors=(
            "浅蓝色",
        ),
        avoided_colors=(
            "荧光色",
        ),
        preferred_fits=(
            "宽松",
        ),
        avoided_materials=(
            "粗糙羊毛",
        ),
        common_scenarios=(
            "通勤",
            "周末出游",
        ),
        typical_budget_min=Decimal(100),
        typical_budget_max=Decimal(500),
        notes="不需要过于正式",
    )


def test_build_style_profile_context_excludes_user_id() -> None:
    """验证档案上下文包含偏好但不泄露内部用户 ID。"""

    context = build_style_profile_context(
        create_style_profile(),
    )

    assert "简约、休闲" in context
    assert "希望避免的风格：街头" in context
    assert "浅蓝色" in context
    assert "100 至 500 元" in context
    assert "不需要过于正式" in context
    assert "user-001" not in context


@pytest.mark.anyio
async def test_load_style_profile_uses_current_user() -> None:
    """验证节点使用绑定的当前用户查询档案。"""

    repository = AsyncMock(
        spec=StyleProfileRepository,
    )
    repository.get_by_user_id.return_value = (
        create_style_profile()
    )
    node = create_load_style_profile_node(
        repository=repository,
        user_id="user-001",
    )

    result = await node(
        {
            "messages": [],
        },
    )

    assert "喜欢的风格：简约、休闲" in (
        result["style_profile_context"]
    )
    repository.get_by_user_id.assert_awaited_once_with(
        "user-001",
    )


@pytest.mark.anyio
async def test_load_style_profile_clears_missing_profile() -> None:
    """验证没有档案时清空 Checkpointer 中可能存在的旧上下文。"""

    repository = AsyncMock(
        spec=StyleProfileRepository,
    )
    repository.get_by_user_id.return_value = None
    node = create_load_style_profile_node(
        repository=repository,
        user_id="user-001",
    )

    result = await node(
        {
            "messages": [],
            "style_profile_context": "旧档案",
        },
    )

    assert result == {
        "style_profile_context": "",
    }
