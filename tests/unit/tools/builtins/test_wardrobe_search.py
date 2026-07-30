"""用户衣橱搜索工具测试。"""

import json

import pytest

from app.db.repositories.in_memory_wardrobe import (
    InMemoryWardrobeRepository,
)
from app.domain.entities.wardrobe_item import WardrobeItem
from app.tools.builtins.wardrobe_search import (
    create_wardrobe_search_tool,
)


@pytest.mark.anyio
async def test_wardrobe_tool_returns_only_user_available_items() -> None:
    """验证工具只返回当前用户可以穿的衣物。"""

    repository = InMemoryWardrobeRepository(
        items=[
            WardrobeItem(
                wardrobe_item_id="shirt-001",
                user_id="user-001",
                name="浅蓝色亚麻衬衫",
                category="衬衫",
                status="available",
            ),
            WardrobeItem(
                wardrobe_item_id="pants-001",
                user_id="user-001",
                name="暂不可用的黑色西裤",
                category="长裤",
                status="unavailable",
            ),
            WardrobeItem(
                wardrobe_item_id="shirt-002",
                user_id="user-002",
                name="其他用户的白色衬衫",
                category="衬衫",
                status="available",
            ),
        ],
    )

    # 创建只绑定用户一的衣橱工具
    wardrobe_search = create_wardrobe_search_tool(
        repository=repository,
        user_id="user-001",
    )

    result = await wardrobe_search.ainvoke(
        {
            "category": None,
            "limit": 20,
        },
    )

    wardrobe_data = json.loads(result)

    # 只应返回用户一当前可用的衬衫
    assert len(wardrobe_data) == 1
    assert wardrobe_data[0]["wardrobe_item_id"] == "shirt-001"
    # 用户 ID 是内部身份信息，不需要暴露给模型
    assert "user_id" not in wardrobe_data[0]
    assert wardrobe_data[0]["status"] == "available"


def test_wardrobe_tool_does_not_expose_user_id() -> None:
    """验证模型输入参数中没有用户 ID。"""

    repository = InMemoryWardrobeRepository()

    wardrobe_search = create_wardrobe_search_tool(
        repository=repository,
        user_id="user-001",
    )

    # args_schema 描述模型能够自行填写的参数
    args_schema = wardrobe_search.args_schema

    assert args_schema is not None

    # user_id 由应用层通过闭包注入，不能暴露给模型
    assert "user_id" not in args_schema.model_fields

    # 模型只允许控制品类和返回数量
    assert set(args_schema.model_fields) == {
        "category",
        "limit",
    }
