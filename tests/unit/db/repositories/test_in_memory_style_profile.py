"""用户穿搭档案内存仓库测试。"""

import pytest

from app.db.repositories.in_memory_style_profile import (
    InMemoryStyleProfileRepository,
)
from app.domain.entities.style_profile import StyleProfile


@pytest.mark.anyio
async def test_repository_saves_updates_and_deletes_profile() -> None:
    """验证档案仓库完整的创建、更新和删除流程。"""

    repository = InMemoryStyleProfileRepository()

    # 尚未保存档案时应该返回 None
    assert (
        await repository.get_by_user_id("user-001")
        is None
    )

    original_profile = StyleProfile(
        user_id="user-001",
        preferred_styles=("简约",),
    )

    # 第一次保存相当于创建档案
    saved_profile = await repository.save(
        original_profile,
    )

    assert saved_profile is original_profile
    assert (
        await repository.get_by_user_id("user-001")
        == original_profile
    )

    # 使用新对象表示用户更新后的档案
    updated_profile = StyleProfile(
        user_id="user-001",
        preferred_styles=(
            "简约",
            "通勤",
        ),
        notes="通勤穿搭不要过于正式",
    )

    # 相同 user_id 应替换旧档案
    await repository.save(updated_profile)

    assert (
        await repository.get_by_user_id("user-001")
        == updated_profile
    )

    # 第一次删除应该成功
    assert (
        await repository.delete_by_user_id(
            "user-001",
        )
        is True
    )

    # 删除后无法再查询到档案
    assert (
        await repository.get_by_user_id("user-001")
        is None
    )

    # 重复删除不存在的档案应该返回 False
    assert (
        await repository.delete_by_user_id(
            "user-001",
        )
        is False
    )


@pytest.mark.anyio
async def test_repository_loads_initial_profiles() -> None:
    """验证仓库可以使用已有档案初始化。"""

    profile = StyleProfile(
        user_id="user-001",
        preferred_colors=("黑色", "灰色"),
    )

    repository = InMemoryStyleProfileRepository(
        profiles=[profile],
    )

    assert (
        await repository.get_by_user_id("user-001")
        == profile
    )