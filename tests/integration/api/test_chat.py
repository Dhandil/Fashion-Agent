from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from app.main import create_app
from app.core.exceptions import ConfigurationError

# 创建测试应用和客户端
application = create_app()
client = TestClient(application)


def test_chat_returns_agent_response() -> None:
    """验证聊天接口能够返回 Agent 回复。"""

    # 创建假的 Agent Graph
    fake_graph = Mock()

    # 指定假工作流执行后的最终状态
    fake_graph.ainvoke = AsyncMock(
        return_value = {
            "messages": [
                AIMessage(content="请告诉我你的预算"),
            ],
            "knowledge_sources": [
                "data/samples/fabrics.md",
            ],
        },
    )

    # 替换聊天路由中使用的真实 Agent Graph
    with patch(
        "app.api.routers.chat.get_shopping_graph",
        return_value=fake_graph,
    ):
        response = client.post(
            "/api/v1/chat",
            json={
                "message": "我想买一件衬衫",
                "conversation_id": "test-conversation-id",
            },
        )

    # 验证 HTTP 请求成功
    assert response.status_code == 200

    # 验证 API 返回了假 Agent 的回复
    assert response.json() == {
        "conversation_id": "test-conversation-id",
        "message": "请告诉我你的预算",
        "sources": [
            "data/samples/fabrics.md",
        ],
    }

    # 验证工作流只执行了一次
    fake_graph.ainvoke.assert_called_once()

    # 读取传给工作流的初始状态
    input_state = fake_graph.ainvoke.call_args.args[0]

    assert input_state["messages"][0].content == "我想买一件衬衫"

    # 读取传给工作流的执行配置
    graph_config = fake_graph.ainvoke.call_args.kwargs["config"]

    # 验证会话 ID 被作为 Langgraph thread_id 传入
    assert graph_config == {
        "configurable": {
            "thread_id": "test-conversation-id",
        },
    }

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


def test_chat_returns_structured_configuration_error() -> None:
    """验证 LLM 配置缺失时返回统一错误响应。"""

    # 模拟 Agent 服务在创建工作流时抛出配置异常
    with patch(
        "app.api.routers.chat.get_shopping_graph",
        side_effect=ConfigurationError("缺少 LLM_API_KEY 配置"),
    ):
        response = client.post(
            "/api/v1/chat",
            json={
                "message": "我想买一件衬衫",
            },
        )

    # 配置问题属于服务暂时不可用
    assert response.status_code == 503

    # 验证错误响应采用统一结构
    assert response.json() == {
        "code": "configuration_error",
        "message": "缺少 LLM_API_KEY 配置",
    }


def test_chat_generates_conversation_id() -> None:
    """验证首次聊天会自动生成会话 ID。"""

    # 创建假的 Agent Graph
    fake_graph = Mock()
    fake_graph.ainvoke = AsyncMock(
        return_value={
            "messages": [
                AIMessage(
                    content="请告诉我你的预算",
                ),
            ],
        },
    )

    # 替换真实 Agent Graph，避免调用 LLM
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

    assert response.status_code == 200

    # 取得响应 JSON 和服务端生成的会话 ID
    response_data = response.json()
    conversation_id = response_data["conversation_id"]

    # UUID() 能成功解析，说明返回值是合法 UUID
    assert UUID(conversation_id)

    # 验证 Agent 回复
    assert response_data["message"] == "请告诉我你的预算"

    # 验证生成的 ID 被传给 Langgraph
    graph_config = fake_graph.ainvoke.call_args.kwargs["config"]
    assert graph_config["configurable"]["thread_id"] == conversation_id