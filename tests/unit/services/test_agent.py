from unittest.mock import Mock, patch

from app.services.agent import get_shopping_graph


def test_get_shopping_graph_builds_and_caches_graph() -> None:
    """验证服务层会创建并缓存购物 Agent 工作流。"""

    # 清楚其他测试或调用可能留下的缓存
    get_shopping_graph.cache_clear()

    # 创建假的模型、Checkpointer 和编译图对象
    fake_model = Mock()
    fake_checkpointer = Mock()
    fake_retriever = Mock()
    fake_graph = Mock()

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
            "app.services.agent.create_shopping_graph",
            return_value=fake_graph,
        ) as mocked_create_graph,
    ):
        # 第一次调用会完成依赖装配
        first_graph = get_shopping_graph()

        # 第二次调用应该直接读取缓存
        second_graph = get_shopping_graph()

    # 两次调用应该返回同一个图对象
    assert first_graph is fake_graph
    assert second_graph is fake_graph

    # 模型、Checkpointer 和图都应该只创建或获取一次
    mocked_create_model.assert_called_once_with()
    mocked_get_checkpointer.assert_called_once_with()
    mocked_get_retriever.assert_called_once_with()

    mocked_create_graph.assert_called_once_with(
        model=fake_model,
        checkpointer=fake_checkpointer,
        retriever=fake_retriever,
    )

    # 测试结束后清楚缓存，避免影响其他测试
    get_shopping_graph.cache_clear()