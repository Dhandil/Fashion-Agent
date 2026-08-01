"""Fashion Agent 服务装配测试。"""

from unittest.mock import (
    AsyncMock,
    Mock,
    patch,
)

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
)
from langchain_core.retrievers import BaseRetriever
from langgraph.checkpoint.memory import InMemorySaver

from app.agents.schemas.outfit import (
    OutfitGenerationResult,
)
from app.domain.entities.outfit import (
    OutfitItem,
    OutfitRecommendation,
)
from app.domain.entities.wardrobe_item import (
    WardrobeItem,
    WardrobeItemStatus,
)
from app.domain.repositories.outfit import OutfitRepository
from app.domain.repositories.outfit_feedback import (
    OutfitFeedbackRepository,
)
from app.domain.repositories.style_profile import (
    StyleProfileRepository,
)
from app.domain.repositories.wardrobe import (
    WardrobeRepository,
)
from app.services.agent import (
    ShoppingAgentRuntime,
    create_user_shopping_graph,
    get_shopping_agent_runtime,
)
from app.tools.registry.registry import ToolRegistry


def test_get_shopping_agent_runtime_caches_shared_resources() -> None:
    """验证无请求状态的 Agent 资源只创建一次。"""

    get_shopping_agent_runtime.cache_clear()

    fake_model = Mock()
    fake_checkpointer = Mock()
    fake_retriever = Mock()
    fake_settings = Mock(
        agent_context_max_chars=4_321,
    )

    with (
        patch(
            "app.services.agent.create_chat_model",
            return_value=fake_model,
        ) as mocked_create_model,
        patch(
            "app.services.agent.get_short_term_checkpointer",
            return_value=fake_checkpointer,
        ) as mocked_get_checkpointer,
        patch(
            "app.services.agent.get_knowledge_retriever",
            return_value=fake_retriever,
        ) as mocked_get_retriever,
        patch(
            "app.services.agent.get_settings",
            return_value=fake_settings,
        ) as mocked_get_settings,
    ):
        first_runtime = get_shopping_agent_runtime()
        second_runtime = get_shopping_agent_runtime()

    assert first_runtime is second_runtime
    assert first_runtime.model is fake_model
    assert first_runtime.checkpointer is fake_checkpointer
    assert first_runtime.retriever is fake_retriever
    assert first_runtime.context_max_chars == 4_321

    mocked_create_model.assert_called_once_with()
    mocked_get_checkpointer.assert_called_once_with()
    mocked_get_retriever.assert_called_once_with()
    mocked_get_settings.assert_called_once_with()

    get_shopping_agent_runtime.cache_clear()


def test_create_user_shopping_graph_keeps_request_tools_uncached() -> None:
    """验证每次请求都会重新绑定当前用户的衣橱工具。"""

    fake_runtime = ShoppingAgentRuntime(
        model=Mock(),
        checkpointer=Mock(),
        retriever=Mock(),
    )
    fake_repository = Mock()
    fake_outfit_repository = Mock()
    fake_feedback_repository = Mock()
    fake_style_profile_repository = Mock()

    fake_tools = (
        Mock(),
        Mock(),
    )
    fake_registry = Mock()
    fake_registry.list_tools.return_value = fake_tools

    first_graph = Mock()
    second_graph = Mock()

    with (
        patch(
            "app.services.agent.get_shopping_agent_runtime",
            return_value=fake_runtime,
        ),
        patch(
            "app.services.agent.create_request_tool_registry",
            return_value=fake_registry,
        ) as mocked_create_registry,
        patch(
            "app.services.agent.create_shopping_graph",
            side_effect=[
                first_graph,
                second_graph,
            ],
        ) as mocked_create_graph,
    ):
        first_result = create_user_shopping_graph(
            wardrobe_repository=fake_repository,
            outfit_repository=fake_outfit_repository,
            outfit_feedback_repository=(fake_feedback_repository),
            style_profile_repository=(fake_style_profile_repository),
            user_id="user-001",
        )
        second_result = create_user_shopping_graph(
            wardrobe_repository=fake_repository,
            outfit_repository=fake_outfit_repository,
            outfit_feedback_repository=(fake_feedback_repository),
            style_profile_repository=(fake_style_profile_repository),
            user_id="user-001",
        )

    assert first_result is first_graph
    assert second_result is second_graph

    # 请求注册表和 Graph 都不能因共享运行资源而被全局缓存
    assert mocked_create_registry.call_count == 2
    assert mocked_create_graph.call_count == 2
    assert fake_registry.list_tools.call_count == 2

    mocked_create_registry.assert_called_with(
        wardrobe_repository=fake_repository,
        user_id="user-001",
        weather_provider=None,
    )
    mocked_create_graph.assert_called_with(
        model=fake_runtime.model,
        checkpointer=fake_runtime.checkpointer,
        retriever=fake_runtime.retriever,
        tools=fake_tools,
        outfit_repository=fake_outfit_repository,
        outfit_feedback_repository=(fake_feedback_repository),
        style_profile_repository=(fake_style_profile_repository),
        user_id="user-001",
        context_max_chars=fake_runtime.context_max_chars,
    )


@pytest.mark.anyio
async def test_user_graph_executes_scoped_wardrobe_tool() -> None:
    """验证请求级 Graph 能执行绑定当前用户的衣橱查询。"""

    model = Mock(spec=BaseChatModel)
    tool_enabled_model = Mock(spec=BaseChatModel)
    model.bind_tools.return_value = tool_enabled_model

    # 结构化输出模型负责把本轮文本回复整理为可追溯 Outfit
    structured_model = Mock()
    model.with_structured_output.return_value = structured_model
    recommendation = OutfitRecommendation(
        name="夏季通勤搭配",
        scenario="通勤",
        items=[
            OutfitItem(
                role="上装",
                name="浅蓝色亚麻衬衫",
                source="wardrobe",
                source_reference_id="shirt-001",
                reason="透气并适合通勤",
            ),
        ],
        recommendation_reason="使用已有衬衫完成通勤搭配。",
    )
    structured_model.invoke.return_value = OutfitGenerationResult(
        outfit=recommendation,
    )

    # 第一条回复要求查询衣橱，第二条回复整理最终穿搭建议
    tool_enabled_model.invoke.side_effect = [
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "search_wardrobe",
                    "args": {
                        "category": "衬衫",
                        "limit": 20,
                    },
                    "id": "wardrobe-call-1",
                    "type": "tool_call",
                },
            ],
        ),
        AIMessage(
            content="可以使用浅蓝色亚麻衬衫完成通勤搭配。",
        ),
    ]

    retriever = Mock(spec=BaseRetriever)
    retriever.invoke.return_value = []

    runtime = ShoppingAgentRuntime(
        model=model,
        checkpointer=InMemorySaver(),
        retriever=retriever,
    )

    wardrobe_repository = Mock(
        spec=WardrobeRepository,
    )
    wardrobe_repository.search = AsyncMock(
        return_value=[
            WardrobeItem(
                wardrobe_item_id="shirt-001",
                user_id="user-001",
                name="浅蓝色亚麻衬衫",
                category="衬衫",
            ),
        ],
    )
    outfit_repository = Mock(
        spec=OutfitRepository,
    )
    outfit_repository.search = AsyncMock(
        return_value=[],
    )
    outfit_repository.get_by_ids = AsyncMock(
        return_value=[],
    )
    feedback_repository = Mock(
        spec=OutfitFeedbackRepository,
    )
    feedback_repository.search = AsyncMock(
        return_value=[],
    )
    style_profile_repository = Mock(
        spec=StyleProfileRepository,
    )
    style_profile_repository.get_by_user_id = AsyncMock(
        return_value=None,
    )

    # 本测试不需要商品工具，只验证请求级衣橱工具链路
    shared_registry = ToolRegistry()

    with (
        patch(
            "app.services.agent.get_shopping_agent_runtime",
            return_value=runtime,
        ),
        patch(
            "app.tools.registry.provider.get_tool_registry",
            return_value=shared_registry,
        ),
    ):
        graph = create_user_shopping_graph(
            wardrobe_repository=wardrobe_repository,
            outfit_repository=outfit_repository,
            outfit_feedback_repository=(feedback_repository),
            style_profile_repository=(style_profile_repository),
            user_id="user-001",
        )

        result = await graph.ainvoke(
            {
                "messages": [
                    HumanMessage(
                        content="请用我的衣橱搭配通勤服装",
                    ),
                ],
            },
            config={
                "configurable": {
                    "thread_id": ("user:user-001:conversation:wardrobe-test"),
                },
            },
        )

    wardrobe_repository.search.assert_awaited_once_with(
        user_id="user-001",
        category="衬衫",
        status=WardrobeItemStatus.AVAILABLE,
        limit=20,
    )
    outfit_repository.search.assert_awaited_once_with(
        user_id="user-001",
        scenario=None,
        favorite_only=False,
        limit=5,
        offset=0,
    )
    feedback_repository.search.assert_awaited_once_with(
        user_id="user-001",
        limit=20,
    )
    style_profile_repository.get_by_user_id.assert_awaited_once_with(
        "user-001",
    )
    outfit_repository.get_by_ids.assert_not_awaited()
    assert result["messages"][-1].content == ("可以使用浅蓝色亚麻衬衫完成通勤搭配。")
    assert result["outfit_recommendation"] == recommendation
