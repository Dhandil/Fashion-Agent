"""用户 Outfit 反馈加载节点测试。"""

from unittest.mock import AsyncMock

import pytest

from app.agents.nodes.load_outfit_feedback import (
    build_outfit_feedback_context,
    create_load_outfit_feedback_node,
)
from app.agents.state.shopping import ShoppingAgentState
from app.domain.entities.outfit import Outfit, OutfitItem
from app.domain.entities.outfit_feedback import (
    OutfitFeedback,
    OutfitFeedbackSentiment,
)
from app.domain.repositories.outfit import OutfitRepository
from app.domain.repositories.outfit_feedback import (
    OutfitFeedbackRepository,
)


def create_outfit() -> Outfit:
    """创建能够说明历史偏好的已保存穿搭。"""

    return Outfit(
        outfit_id="outfit-001",
        user_id="user-001",
        name="清爽通勤搭配",
        scenario="通勤",
        style_tags=(
            "简约",
            "清爽",
        ),
        items=(
            OutfitItem(
                role="上装",
                name="浅蓝色亚麻衬衫",
                source="wardrobe",
                source_reference_id="shirt-001",
            ),
        ),
        recommendation_reason="适合夏季通勤。",
    )


def test_build_outfit_feedback_context_combines_outfit() -> None:
    """验证态度、说明和原穿搭内容被组合为偏好上下文。"""

    context = build_outfit_feedback_context(
        feedback_items=(
            OutfitFeedback(
                user_id="user-001",
                outfit_id="outfit-001",
                sentiment=OutfitFeedbackSentiment.LIKE,
                comment="喜欢清爽配色",
            ),
        ),
        outfits=(
            create_outfit(),
        ),
    )

    assert "清爽通勤搭配" in context
    assert "简约、清爽" in context
    assert "浅蓝色亚麻衬衫" in context
    assert "用户态度：喜欢" in context
    assert "喜欢清爽配色" in context


@pytest.mark.anyio
async def test_load_outfit_feedback_uses_two_batch_queries() -> None:
    """验证节点通过反馈查询和 Outfit 批量查询构建上下文。"""

    feedback = OutfitFeedback(
        user_id="user-001",
        outfit_id="outfit-001",
        sentiment=OutfitFeedbackSentiment.DISLIKE,
        comment="不喜欢过于正式",
    )
    outfit_repository = AsyncMock(
        spec=OutfitRepository,
    )
    outfit_repository.get_by_ids.return_value = [
        create_outfit(),
    ]
    feedback_repository = AsyncMock(
        spec=OutfitFeedbackRepository,
    )
    feedback_repository.search.return_value = [
        feedback,
    ]
    node = create_load_outfit_feedback_node(
        outfit_repository=outfit_repository,
        feedback_repository=feedback_repository,
        user_id="user-001",
    )
    state: ShoppingAgentState = {
        "messages": [],
    }

    result = await node(state)

    assert "用户态度：不喜欢" in (
        result["outfit_feedback_context"]
    )
    feedback_repository.search.assert_awaited_once_with(
        user_id="user-001",
        limit=20,
    )
    outfit_repository.get_by_ids.assert_awaited_once_with(
        user_id="user-001",
        outfit_ids=(
            "outfit-001",
        ),
    )


@pytest.mark.anyio
async def test_load_outfit_feedback_skips_outfit_query_when_empty() -> None:
    """验证没有反馈时清空旧上下文且不查询 Outfit。"""

    outfit_repository = AsyncMock(
        spec=OutfitRepository,
    )
    feedback_repository = AsyncMock(
        spec=OutfitFeedbackRepository,
    )
    feedback_repository.search.return_value = []
    node = create_load_outfit_feedback_node(
        outfit_repository=outfit_repository,
        feedback_repository=feedback_repository,
        user_id="user-001",
    )

    result = await node(
        {
            "messages": [],
            "outfit_feedback_context": "旧反馈",
        },
    )

    assert result == {
        "outfit_feedback_context": "",
    }
    outfit_repository.get_by_ids.assert_not_awaited()
