from unittest.mock import Mock, patch

from app.services.agent import get_shopping_graph


def test_get_shopping_graph_builds_and_caches_graph() -> None:
    """验证服务层会创建并缓存购物 Agent 工作流。"""

    # 清楚其他测试或调用可能留下的缓存
    get_shopping_graph.cache_clear()

    # 创建假的模型对象和编译对象
    fake_model = Mock()
    fake_graph = Mock()

    # 临时替换模型工厂和图工厂，避免读取真实配置
    with (
        patch(
            "app.services.agent.create_chat_model",
            return_value=fake_model,
        ) as mocked_craete_model,
        patch(
            "app.services.agent.create_shopping_graph",
            return_value=fake_graph,
        ) as mocked_create_graph,
    ):
        # 第一次调用会创建模型并编译图
        first_graph = get_shopping_graph()

        # 第二次调用应该直接读取缓存
        second_graph = get_shopping_graph()

    # 两次调用应该返回同一个图对象
    assert first_graph is fake_graph
    assert second_graph is fake_graph

    # 模型和图都应该只创建一次
    mocked_craete_model.assert_called_once_with()
    mocked_create_graph.assert_called_once_with(fake_model)

    # 测试结束后清楚缓存，避免影响其他测试
    get_shopping_graph.cache_clear()