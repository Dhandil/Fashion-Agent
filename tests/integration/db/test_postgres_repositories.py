"""PostgreSQL 用户时尚数据仓库集成测试。"""

import os
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.db.repositories.fashion_provider import (
    create_postgres_fashion_repositories,
)
from app.db.session import get_session_factory
from app.domain.entities.outfit import (
    Outfit,
    OutfitItem,
    OutfitItemSource,
)
from app.domain.entities.preference_candidate import (
    PreferenceCandidateCategory,
    PreferenceDirection,
)
from app.domain.entities.preference_memory import (
    PreferenceMemory,
    PreferenceMemorySource,
)
from app.domain.entities.style_profile import (
    StyleProfile,
)
from app.domain.entities.wardrobe_item import (
    WardrobeItem,
    WardrobeItemStatus,
)

# 只有明确启用 PostgreSQL 集成测试时才连接本地数据库
pytestmark = pytest.mark.skipif(
    os.getenv("RUN_POSTGRES_TESTS") != "true",
    reason="需要设置 RUN_POSTGRES_TESTS=true 并启动 PostgreSQL",
)


@pytest.mark.anyio
async def test_style_profile_round_trip_with_postgres() -> None:
    """验证用户穿搭档案能够真实写入并从 PostgreSQL 读取。"""

    session_factory = get_session_factory()

    # 一个测试使用一个独立的异步 Session
    async with session_factory() as session:
        repositories = (
            create_postgres_fashion_repositories(
                session,
            )
        )

        profile = StyleProfile(
            user_id="integration-user-001",
            preferred_styles=(
                "简约",
                "通勤",
            ),
            preferred_colors=(
                "黑色",
                "浅蓝色",
            ),
            avoided_colors=(
                "亮黄色",
            ),
            preferred_fits=(
                "宽松",
            ),
            avoided_materials=(
                "粗糙羊毛",
            ),
            common_scenarios=(
                "通勤",
                "休闲",
            ),
            typical_budget_min=Decimal("200.00"),
            typical_budget_max=Decimal("500.00"),
            notes="PostgreSQL 集成测试档案",
        )

        try:
            # 真实执行 INSERT 或 UPDATE
            await repositories.style_profiles.save(
                profile,
            )

            # 使用同一个仓库从数据库重新读取
            found_profile = (
                await repositories.style_profiles.get_by_user_id(
                    profile.user_id,
                )
            )

            assert found_profile == profile

        finally:
            # 无论测试成功还是失败，都回滚测试事务
            await session.rollback()


@pytest.mark.anyio
async def test_wardrobe_and_outfit_round_trip_with_postgres() -> None:
    """验证衣橱单品和完整穿搭能够真实写入并读取。"""

    session_factory = get_session_factory()

    async with session_factory() as session:
        repositories = (
            create_postgres_fashion_repositories(
                session,
            )
        )

        wardrobe_item = WardrobeItem(
            wardrobe_item_id="integration-wardrobe-001",
            user_id="integration-user-002",
            name="浅蓝色亚麻衬衫",
            category="衬衫",
            colors=(
                "浅蓝色",
            ),
            materials=(
                "亚麻",
                "棉",
            ),
            size="M",
            style_tags=(
                "简约",
                "通勤",
            ),
            seasons=(
                "夏季",
            ),
            scenarios=(
                "通勤",
            ),
            status=WardrobeItemStatus.AVAILABLE,
        )

        outfit = Outfit(
            outfit_id="integration-outfit-001",
            user_id="integration-user-002",
            name="夏季通勤穿搭",
            scenario="通勤",
            style_tags=(
                "简约",
                "清爽",
            ),
            season="夏季",
            items=(
                OutfitItem(
                    role="上装",
                    name="浅蓝色亚麻衬衫",
                    source=OutfitItemSource.WARDROBE,
                    source_reference_id=(
                        wardrobe_item.wardrobe_item_id
                    ),
                    reason="透气且适合夏季通勤",
                ),
                OutfitItem(
                    role="下装",
                    name="米色直筒裤",
                    source=(
                        OutfitItemSource.RECOMMENDATION
                    ),
                    reason="与浅蓝色上装搭配协调",
                ),
            ),
            recommendation_reason=(
                "使用用户已有衬衫完成清爽的夏季通勤搭配。"
            ),
        )

        try:
            # 真实保存衣橱单品和穿搭方案
            await repositories.wardrobe.save(
                wardrobe_item,
            )
            await repositories.outfits.save(outfit)

            # 从 PostgreSQL 重新读取两个领域实体
            found_item = await repositories.wardrobe.get_by_id(
                user_id=wardrobe_item.user_id,
                wardrobe_item_id=(
                    wardrobe_item.wardrobe_item_id
                ),
            )
            found_outfit = await repositories.outfits.get_by_id(
                user_id=outfit.user_id,
                outfit_id=outfit.outfit_id,
            )

            assert found_item == wardrobe_item
            assert found_outfit == outfit

            # 验证 Outfit 子表中的单品顺序和来源
            assert found_outfit is not None
            assert found_outfit.items[0].name == (
                "浅蓝色亚麻衬衫"
            )
            assert (
                found_outfit.items[0].source
                is OutfitItemSource.WARDROBE
            )
            assert found_outfit.items[1].name == (
                "米色直筒裤"
            )

        finally:
            # 不在开发数据库中保留集成测试数据
            await session.rollback()


@pytest.mark.anyio
async def test_outfit_update_replaces_child_items() -> None:
    """验证更新穿搭时数据库会替换旧的组成单品。"""

    session_factory = get_session_factory()

    async with session_factory() as session:
        repositories = (
            create_postgres_fashion_repositories(
                session,
            )
        )

        original_outfit = Outfit(
            outfit_id="integration-outfit-update-001",
            user_id="integration-user-003",
            name="初始通勤穿搭",
            scenario="通勤",
            items=(
                OutfitItem(
                    role="上装",
                    name="白色衬衫",
                    source=(
                        OutfitItemSource.RECOMMENDATION
                    ),
                ),
                OutfitItem(
                    role="下装",
                    name="黑色直筒裤",
                    source=(
                        OutfitItemSource.RECOMMENDATION
                    ),
                ),
            ),
            recommendation_reason="基础黑白通勤搭配。",
        )

        # frozen 领域实体不直接修改，而是创建一个新版本
        updated_outfit = original_outfit.model_copy(
            update={
                "name": "更新后的通勤穿搭",
                "items": (
                    OutfitItem(
                        role="连衣裙",
                        name="藏蓝色衬衫裙",
                        source=(
                            OutfitItemSource.RECOMMENDATION
                        ),
                    ),
                ),
                "recommendation_reason": (
                    "使用一件式衬衫裙简化通勤搭配。"
                ),
                "is_favorite": True,
            },
        )

        try:
            # 第一次保存两个子单品
            await repositories.outfits.save(
                original_outfit,
            )

            # 使用相同复合主键保存新版本
            await repositories.outfits.save(
                updated_outfit,
            )

            # 清除 Session 中的已加载状态
            # 确保下面的查询读取数据库当前结果
            session.expire_all()

            found_outfit = await repositories.outfits.get_by_id(
                user_id=updated_outfit.user_id,
                outfit_id=updated_outfit.outfit_id,
            )

            assert found_outfit == updated_outfit
            assert found_outfit is not None

            # 原来的两个单品应该被一个新单品替换
            assert len(found_outfit.items) == 1
            assert found_outfit.items[0].name == (
                "藏蓝色衬衫裙"
            )
            assert found_outfit.is_favorite is True

        finally:
            await session.rollback()


@pytest.mark.anyio
async def test_preference_memory_round_trip_with_postgres() -> None:
    """验证已确认偏好的来源和时间能够真实持久化。"""

    session_factory = get_session_factory()
    async with session_factory() as session:
        repositories = (
            create_postgres_fashion_repositories(
                session,
            )
        )
        profile = StyleProfile(
            user_id="integration-memory-user",
            preferred_styles=("休闲",),
        )
        confirmed_at = datetime(
            2026,
            8,
            2,
            10,
            tzinfo=UTC,
        )
        memory = PreferenceMemory(
            preference_memory_id=(
                "pm_0123456789abcdef0123456789abcdef"
            ),
            user_id=profile.user_id,
            category=PreferenceCandidateCategory.STYLE,
            value="休闲",
            direction=PreferenceDirection.PREFER,
            source=(
                PreferenceMemorySource.OUTFIT_FEEDBACK_CONFIRMATION
            ),
            source_reference_ids=(
                "outfit-001",
                "outfit-002",
            ),
            confirmed_at=confirmed_at,
            last_confirmed_at=confirmed_at,
        )

        try:
            await repositories.style_profiles.save(
                profile,
            )
            await repositories.preference_memories.save(
                memory,
            )

            found = (
                await repositories.preference_memories.get_by_identity(
                    user_id=profile.user_id,
                    category=(
                        PreferenceCandidateCategory.STYLE
                    ),
                    value="休闲",
                )
            )
            listed = (
                await repositories.preference_memories.list_by_user_id(
                    profile.user_id,
                )
            )

            assert found == memory
            assert listed == (memory,)

            found_by_id = (
                await repositories.preference_memories.get_by_id(
                    user_id=profile.user_id,
                    preference_memory_id=(
                        memory.preference_memory_id
                    ),
                )
            )
            assert found_by_id == memory

            updated_memory = PreferenceMemory.model_validate(
                {
                    **memory.model_dump(),
                    "expires_at": (
                        confirmed_at + timedelta(days=30)
                    ),
                },
            )
            await repositories.preference_memories.save(
                updated_memory,
            )
            assert (
                await repositories.preference_memories.get_by_id(
                    user_id=profile.user_id,
                    preference_memory_id=(
                        memory.preference_memory_id
                    ),
                )
                == updated_memory
            )

            assert (
                await repositories.preference_memories.delete_by_id(
                    user_id=profile.user_id,
                    preference_memory_id=(
                        memory.preference_memory_id
                    ),
                )
                is True
            )
            assert (
                await repositories.preference_memories.delete_by_id(
                    user_id=profile.user_id,
                    preference_memory_id=(
                        memory.preference_memory_id
                    ),
                )
                is False
            )
        finally:
            await session.rollback()
