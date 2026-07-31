"""近期 Outfit 上下文加载节点测试。"""

from unittest.mock import AsyncMock

import pytest

from app.agents.nodes.load_recent_outfits import (
    build_recent_outfits_context,
    create_load_recent_outfits_node,
)
from app.domain.entities.outfit import Outfit, OutfitItem
from app.domain.repositories.outfit import OutfitRepository


def create_recent_outfit() -> Outfit:
    """创建包含真实衣橱引用的近期 Outfit。"""

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
            OutfitItem(
                role="下装",
                name="米色直筒裤",
                source="recommendation",
            ),
        ),
        recommendation_reason="适合夏季通勤。",
    )


def test_build_recent_outfits_context_keeps_item_combination() -> None:
    """验证近期上下文保留场景、风格和衣橱组合证据。"""

    context = build_recent_outfits_context(
        (
            create_recent_outfit(),
        ),
    )

    assert "清爽通勤搭配" in context
    assert "场景：通勤" in context
    assert "风格：简约、清爽" in context
    assert "上装：浅蓝色亚麻衬衫" in context
    assert "衣橱 ID：shirt-001" in context
    assert "下装：米色直筒裤" in context


@pytest.mark.anyio
async def test_load_recent_outfits_queries_current_user() -> None:
    """验证节点只查询当前用户最近保存的有限 Outfit。"""

    repository = AsyncMock(
        spec=OutfitRepository,
    )
    repository.search.return_value = [
        create_recent_outfit(),
    ]
    node = create_load_recent_outfits_node(
        repository=repository,
        user_id="user-001",
    )

    result = await node(
        {
            "messages": [],
        },
    )

    assert "shirt-001" in (
        result["recent_outfits_context"]
    )
    repository.search.assert_awaited_once_with(
        user_id="user-001",
        scenario=None,
        favorite_only=False,
        limit=5,
        offset=0,
    )


@pytest.mark.anyio
async def test_load_recent_outfits_clears_stale_context() -> None:
    """验证没有历史 Outfit 时清空 Checkpointer 中的旧上下文。"""

    repository = AsyncMock(
        spec=OutfitRepository,
    )
    repository.search.return_value = []
    node = create_load_recent_outfits_node(
        repository=repository,
        user_id="user-001",
    )

    result = await node(
        {
            "messages": [],
            "recent_outfits_context": "旧的近期穿搭",
        },
    )

    assert result == {
        "recent_outfits_context": "",
    }

