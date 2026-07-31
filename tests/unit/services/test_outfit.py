"""用户确认保存 Outfit 应用服务测试。"""

from unittest.mock import (
    AsyncMock,
    Mock,
)
from uuid import UUID

import pytest

from app.core.exceptions import (
    OutfitNotFoundError,
    OutfitRecommendationNotFoundError,
)
from app.domain.entities.outfit import (
    OutfitItem,
    OutfitRecommendation,
)
from app.domain.repositories.outfit import OutfitRepository
from app.services.outfit import (
    create_confirmed_outfit,
    get_saved_outfit,
    list_saved_outfits,
    save_confirmed_outfit,
)


def create_recommendation() -> OutfitRecommendation:
    """创建已经通过 Agent 校验的临时穿搭推荐。"""

    return OutfitRecommendation(
        name="夏季通勤搭配",
        scenario="通勤",
        style_tags=[
            "简约",
        ],
        season="夏季",
        items=[
            OutfitItem(
                role="上装",
                name="浅蓝色亚麻衬衫",
                source="wardrobe",
                source_reference_id="shirt-001",
            ),
        ],
        recommendation_reason="优先使用已有衣物。",
    )


@pytest.mark.anyio
async def test_save_confirmed_outfit_uses_current_user_state() -> None:
    """验证服务从当前用户会话读取推荐并保存。"""

    recommendation = create_recommendation()

    graph = Mock()
    graph.aget_state = AsyncMock(
        return_value=Mock(
            values={
                "outfit_recommendation": recommendation,
            },
        ),
    )

    repository = AsyncMock(
        spec=OutfitRepository,
    )
    repository.save.side_effect = lambda outfit: outfit

    saved_outfit = await save_confirmed_outfit(
        graph=graph,
        repository=repository,
        user_id="user-001",
        conversation_id="conversation-001",
    )

    # 服务端根据身份和会话生成归属关系，客户端不能指定 user_id
    assert saved_outfit.user_id == "user-001"
    assert saved_outfit.name == recommendation.name
    assert saved_outfit.items == recommendation.items
    assert UUID(saved_outfit.outfit_id)

    # 读取状态时使用包含用户 ID 的线程键
    graph.aget_state.assert_awaited_once_with(
        {
            "configurable": {
                "thread_id": (
                    "user:user-001:"
                    "conversation:conversation-001"
                ),
            },
        },
    )
    repository.save.assert_awaited_once_with(
        saved_outfit,
    )


@pytest.mark.anyio
async def test_save_confirmed_outfit_is_idempotent() -> None:
    """验证同一用户和会话重复确认不会生成不同 ID。"""

    recommendation = create_recommendation()
    graph = Mock()
    graph.aget_state = AsyncMock(
        return_value=Mock(
            values={
                "outfit_recommendation": recommendation,
            },
        ),
    )

    repository = AsyncMock(
        spec=OutfitRepository,
    )
    repository.save.side_effect = lambda outfit: outfit

    first_outfit = await save_confirmed_outfit(
        graph=graph,
        repository=repository,
        user_id="user-001",
        conversation_id="conversation-001",
    )
    second_outfit = await save_confirmed_outfit(
        graph=graph,
        repository=repository,
        user_id="user-001",
        conversation_id="conversation-001",
    )

    assert first_outfit.outfit_id == (
        second_outfit.outfit_id
    )


@pytest.mark.anyio
async def test_save_confirmed_outfit_requires_recommendation() -> None:
    """验证没有结构化推荐时不能创建空 Outfit。"""

    graph = Mock()
    graph.aget_state = AsyncMock(
        return_value=Mock(
            values={
                "outfit_recommendation": None,
            },
        ),
    )
    repository = AsyncMock(
        spec=OutfitRepository,
    )

    with pytest.raises(
        OutfitRecommendationNotFoundError,
        match="没有可以保存的穿搭推荐",
    ):
        await save_confirmed_outfit(
            graph=graph,
            repository=repository,
            user_id="user-001",
            conversation_id="conversation-001",
        )

    repository.save.assert_not_awaited()


@pytest.mark.anyio
async def test_list_saved_outfits_filters_current_user() -> None:
    """验证列表服务把用户和筛选条件传给仓库。"""

    outfit = create_confirmed_outfit(
        recommendation=create_recommendation(),
        user_id="user-001",
        conversation_id="conversation-001",
    )
    repository = AsyncMock(
        spec=OutfitRepository,
    )
    repository.search.return_value = [
        outfit,
    ]

    result = await list_saved_outfits(
        repository=repository,
        user_id="user-001",
        scenario="通勤",
        favorite_only=True,
        limit=10,
    )

    assert result == [
        outfit,
    ]
    repository.search.assert_awaited_once_with(
        user_id="user-001",
        scenario="通勤",
        favorite_only=True,
        limit=10,
    )


@pytest.mark.anyio
async def test_get_saved_outfit_uses_current_user() -> None:
    """验证详情服务使用当前用户和 Outfit ID 查询。"""

    outfit = create_confirmed_outfit(
        recommendation=create_recommendation(),
        user_id="user-001",
        conversation_id="conversation-001",
    )
    repository = AsyncMock(
        spec=OutfitRepository,
    )
    repository.get_by_id.return_value = outfit

    result = await get_saved_outfit(
        repository=repository,
        user_id="user-001",
        outfit_id=outfit.outfit_id,
    )

    assert result is outfit
    repository.get_by_id.assert_awaited_once_with(
        user_id="user-001",
        outfit_id=outfit.outfit_id,
    )


@pytest.mark.anyio
async def test_get_saved_outfit_hides_missing_record() -> None:
    """验证不存在或属于其他用户的穿搭统一返回未找到。"""

    repository = AsyncMock(
        spec=OutfitRepository,
    )
    repository.get_by_id.return_value = None

    with pytest.raises(
        OutfitNotFoundError,
        match="未找到指定的穿搭方案",
    ):
        await get_saved_outfit(
            repository=repository,
            user_id="user-001",
            outfit_id="unknown-outfit",
        )
