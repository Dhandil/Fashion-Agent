"""用户长期穿搭档案应用服务测试。"""

from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from app.domain.entities.style_profile import StyleProfile
from app.domain.repositories.style_profile import (
    StyleProfileRepository,
)
from app.services.style_profile import (
    get_style_profile,
    replace_style_profile,
)


@pytest.mark.anyio
async def test_get_style_profile_returns_empty_profile() -> None:
    """验证档案不存在时返回空领域实体但不写入仓库。"""

    repository = AsyncMock(
        spec=StyleProfileRepository,
    )
    repository.get_by_user_id.return_value = None

    profile = await get_style_profile(
        repository=repository,
        user_id="user-001",
    )

    assert profile == StyleProfile(
        user_id="user-001",
    )
    repository.save.assert_not_awaited()


@pytest.mark.anyio
async def test_replace_style_profile_uses_current_user() -> None:
    """验证服务用当前用户和明确提交内容替换档案。"""

    repository = AsyncMock(
        spec=StyleProfileRepository,
    )
    repository.save.side_effect = (
        lambda profile: profile
    )

    profile = await replace_style_profile(
        repository=repository,
        user_id="user-001",
        preferred_styles=(
            "简约",
            "休闲",
        ),
        preferred_colors=(
            "浅蓝色",
        ),
        typical_budget_min=Decimal(100),
        typical_budget_max=Decimal(500),
        notes="不要过于正式",
    )

    assert profile.user_id == "user-001"
    assert profile.preferred_styles == (
        "简约",
        "休闲",
    )
    assert profile.preferred_colors == (
        "浅蓝色",
    )
    assert profile.notes == "不要过于正式"
    repository.save.assert_awaited_once_with(
        profile,
    )
