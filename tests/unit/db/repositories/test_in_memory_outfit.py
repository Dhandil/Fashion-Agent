"""穿搭方案内存仓库测试。"""

import pytest

from app.db.repositories.in_memory_outfit import (
    InMemoryOutfitRepository,
)
from app.domain.entities.outfit import (
    Outfit,
    OutfitItem,
    OutfitItemSource,
)


def create_test_outfit(
    outfit_id: str,
    user_id: str,
    scenario: str,
    is_favorite: bool = False,
) -> Outfit:
    """创建测试使用的最小有效穿搭方案。"""

    return Outfit(
        outfit_id=outfit_id,
        user_id=user_id,
        name=f"{scenario}穿搭",
        scenario=scenario,
        items=[
            OutfitItem(
                role="上装",
                name="白色衬衫",
                source=(
                    OutfitItemSource.RECOMMENDATION
                ),
            ),
        ],
        recommendation_reason="适合当前测试场景",
        is_favorite=is_favorite,
    )


@pytest.mark.anyio
async def test_repository_filters_scenario_and_favorite() -> None:
    """验证穿搭仓库能够过滤场景和收藏状态。"""

    repository = InMemoryOutfitRepository(
        outfits=[
            create_test_outfit(
                outfit_id="outfit-001",
                user_id="user-001",
                scenario="通勤",
                is_favorite=True,
            ),
            create_test_outfit(
                outfit_id="outfit-002",
                user_id="user-001",
                scenario="约会",
            ),
            create_test_outfit(
                outfit_id="outfit-003",
                user_id="user-001",
                scenario="通勤",
            ),
            create_test_outfit(
                outfit_id="outfit-004",
                user_id="user-002",
                scenario="通勤",
                is_favorite=True,
            ),
        ],
    )

    # 只查询用户一的通勤穿搭
    commute_outfits = await repository.search(
        user_id="user-001",
        scenario="通勤",
    )

    assert {
        outfit.outfit_id
        for outfit in commute_outfits
    } == {
        "outfit-001",
        "outfit-003",
    }

    # 只查询用户一收藏的穿搭
    favorite_outfits = await repository.search(
        user_id="user-001",
        favorite_only=True,
    )

    assert len(favorite_outfits) == 1
    assert (
        favorite_outfits[0].outfit_id
        == "outfit-001"
    )

    # 数量限制应该截断查询结果
    limited_outfits = await repository.search(
        user_id="user-001",
        limit=1,
        offset=1,
    )

    assert len(limited_outfits) == 1
    assert limited_outfits[0].outfit_id == (
        "outfit-002"
    )

    # 总数不受 limit 和 offset 影响
    assert (
        await repository.count(
            user_id="user-001",
        )
        == 3
    )
    assert (
        await repository.count(
            user_id="user-001",
            scenario="通勤",
        )
        == 2
    )


@pytest.mark.anyio
async def test_repository_isolates_users_and_deletes_outfit() -> None:
    """验证相同穿搭 ID 在不同用户之间保持隔离。"""

    user_one_outfit = create_test_outfit(
        outfit_id="outfit-001",
        user_id="user-001",
        scenario="通勤",
    )
    user_two_outfit = create_test_outfit(
        outfit_id="outfit-001",
        user_id="user-002",
        scenario="约会",
    )

    repository = InMemoryOutfitRepository(
        outfits=[
            user_one_outfit,
            user_two_outfit,
        ],
    )

    assert (
        await repository.get_by_id(
            "user-001",
            "outfit-001",
        )
        == user_one_outfit
    )
    assert (
        await repository.get_by_id(
            "user-002",
            "outfit-001",
        )
        == user_two_outfit
    )

    # 批量查询保持输入顺序，并且不会返回其他用户的数据
    batch_outfits = await repository.get_by_ids(
        user_id="user-001",
        outfit_ids=(
            "missing-outfit",
            "outfit-001",
        ),
    )
    assert batch_outfits == [
        user_one_outfit,
    ]

    # 删除用户一的穿搭
    assert (
        await repository.delete(
            "user-001",
            "outfit-001",
        )
        is True
    )

    # 用户二的同 ID 穿搭不受影响
    assert (
        await repository.get_by_id(
            "user-002",
            "outfit-001",
        )
        == user_two_outfit
    )

    # 重复删除不存在的数据返回 False
    assert (
        await repository.delete(
            "user-001",
            "outfit-001",
        )
        is False
    )
