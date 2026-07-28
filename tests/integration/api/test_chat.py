from unittest.mock import Mock, patch

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from app.main import create_app


# 创建测试应用和客户端
application = create_app()
client = TestClient(application)


def test_chat_returns_agent_response() -> None:
    """验证聊天接口能够返回 Agent 回复。"""

    # 创建假的 Agent Graph
    fake_graph = Mock()

    # 指定假工作流执行后的最终状态
    fake_graph.invoke.return_value = {
        "messages": [
            AIMessage(content="请告诉我你的预算"),
        ],
    }

    # 替换聊天路由中使用的真实 Agent Graph
    with patch(
        "app.api.routers.chat.get_shopping_graph",
        return_value=fake_graph,
    ):
        response = client.post(
            "/api/v1/chat",
            json={
                "message": "我想买一件衬衫",
            },
        )

    # 验证 HTTP 请求成功
    assert response.status_code == 200

    # 验证 API 返回了假 Agent 的回复
    assert response.json() == {
        "message": "请告诉我你的预算",
    }

    # 验证工作流只执行了一次
    fake_graph.invoke.assert_called_once()

    # 读取传给工作流的初始状态
    input_state = fake_graph.invoke.call_args.args[0]

    assert input_state["messages"][0].content == "我想买一件衬衫"


def test_chat_rejects_empty_message() -> None:
    """验证聊天接口拒绝空消息。"""

    # 监控 Agent 服务，确认校验失败时不会调用它
    with patch(
        "app.api.routers.chat.get_shopping_graph",
    ) as mocked_get_graph:
        response = client.post(
            "/api/v1/chat",
            json={
                "message": "",
            },
        )

    # 422 表示请求数据不符合 Pydantic 模型要求
    assert response.status_code == 422

    # 请求校验失败后，路由函数不应该被执行
    mocked_get_graph.assert_not_called()