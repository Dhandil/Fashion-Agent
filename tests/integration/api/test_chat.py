import json
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, ToolMessage

from app.api.dependencies.database import (
    get_fashion_repositories,
)
from app.core.config import (
    Settings,
    get_settings,
)
from app.core.exceptions import ConfigurationError
from app.db.repositories.fashion_provider import (
    FashionRepositories,
)
from app.domain.entities.outfit import (
    OutfitItem,
    OutfitRecommendation,
    WardrobeGap,
)
from app.domain.entities.outfit_gap import (
    CoreOutfitRole,
    OutfitGapNextAction,
    OutfitGapReport,
)
from app.domain.entities.outfit_validation import (
    OutfitFeasibilityIssue,
    OutfitFeasibilityReport,
    OutfitIssueCode,
    OutfitIssueSeverity,
)
from app.domain.repositories.wardrobe import (
    WardrobeRepository,
)
from app.integrations.weather.provider import get_weather_provider
from app.main import create_app

# 创建测试使用的请求级仓库集合
wardrobe_repository = Mock(
    spec=WardrobeRepository,
)
outfit_repository = Mock()
outfit_feedback_repository = Mock()
style_profile_repository = Mock()
repositories = FashionRepositories(
    style_profiles=style_profile_repository,
    preference_memories=Mock(),
    wardrobe=wardrobe_repository,
    outfits=outfit_repository,
    outfit_feedback=outfit_feedback_repository,
)


async def override_repositories() -> FashionRepositories:
    """为聊天接口测试提供假的请求级仓库。"""

    return repositories


def override_settings() -> Settings:
    """确保测试不读取本地 .env 中的运行环境。"""

    return Settings(
        _env_file=None,
        app_env="test",
        debug=False,
        weather_provider_backend="disabled",
    )


def override_weather_provider() -> None:
    """测试聊天 API 时显式关闭外部天气服务。"""

    return


# 创建测试应用，替换数据库仓库和环境配置
application = create_app()
application.dependency_overrides[get_fashion_repositories] = override_repositories
application.dependency_overrides[get_settings] = override_settings
application.dependency_overrides[get_weather_provider] = override_weather_provider
client = TestClient(application)


def test_chat_returns_agent_response() -> None:
    """验证聊天接口能够返回 Agent 回复。"""

    # 创建假的 Agent Graph
    fake_graph = Mock()

    # 指定假工作流执行后的最终状态
    fake_graph.ainvoke = AsyncMock(
        return_value={
            "messages": [
                AIMessage(content="请告诉我你的预算"),
            ],
            "knowledge_sources": [
                "data/samples/fabrics.md",
            ],
        },
    )

    # 替换聊天路由中使用的真实 Agent Graph
    prune_checkpoints = AsyncMock(return_value=True)
    with (
        patch(
            ("app.api.dependencies.agent.create_user_shopping_graph"),
            return_value=fake_graph,
        ) as mocked_create_graph,
        patch(
            "app.api.routers.chat.prune_conversation_checkpoints",
            prune_checkpoints,
        ),
    ):
        response = client.post(
            "/api/v1/chat",
            headers={
                "X-User-ID": "user-001",
            },
            json={
                "message": "我想买一件衬衫",
                "conversation_id": "test-conversation-id",
            },
        )

    # 验证 HTTP 请求成功
    assert response.status_code == 200
    request_id = response.headers["X-Request-ID"]
    assert UUID(request_id)

    # 验证 API 返回了假 Agent 的回复
    assert response.json() == {
        "conversation_id": "test-conversation-id",
        "message": "请告诉我你的预算",
        "weather": None,
        "outfit": None,
        "outfit_gap": None,
        "sources": [
            "data/samples/fabrics.md",
        ],
        "outfit_issues": [],
    }

    # 验证工作流只执行了一次
    fake_graph.ainvoke.assert_called_once()
    prune_checkpoints.assert_awaited_once_with(
        user_id="user-001",
        conversation_id="test-conversation-id",
    )

    # 当前用户和请求级衣橱仓库被绑定到本次 Agent Graph
    mocked_create_graph.assert_called_once_with(
        wardrobe_repository=wardrobe_repository,
        outfit_repository=outfit_repository,
        outfit_feedback_repository=(outfit_feedback_repository),
        style_profile_repository=(style_profile_repository),
        user_id="user-001",
        weather_provider=None,
    )

    # 读取传给工作流的初始状态
    input_state = fake_graph.ainvoke.call_args.args[0]

    assert input_state["messages"][0].content == "我想买一件衬衫"
    # 旧推荐由 Graph 的 prepare_turn 节点清理并保存为调整基线
    assert "outfit_recommendation" not in input_state
    # 未提供天气时明确清空旧的本轮天气，避免跨轮使用过期数据
    assert input_state["weather_context"] is None

    # 读取传给工作流的执行配置
    graph_config = fake_graph.ainvoke.call_args.kwargs["config"]

    # 验证会话 ID 被作为 Langgraph thread_id 传入
    assert graph_config == {
        "configurable": {
            "thread_id": ("user:user-001:conversation:test-conversation-id"),
        },
        "metadata": {
            "request_id": request_id,
        },
    }


def test_chat_rejects_empty_message() -> None:
    """验证聊天接口拒绝空消息。"""

    fake_graph = Mock()
    fake_graph.ainvoke = AsyncMock()

    # 即使依赖已经完成装配，非法请求也不能执行 Agent Graph
    with patch(
        ("app.api.dependencies.agent.create_user_shopping_graph"),
        return_value=fake_graph,
    ):
        response = client.post(
            "/api/v1/chat",
            headers={
                "X-User-ID": "user-001",
            },
            json={
                "message": "",
            },
        )

    # 422 表示请求数据不符合 Pydantic 模型要求
    assert response.status_code == 422

    # 请求校验失败后，工作流不应该被执行
    fake_graph.ainvoke.assert_not_awaited()


def test_chat_requires_current_user_header() -> None:
    """验证聊天接口必须具有当前用户身份。"""

    fake_graph = Mock()
    fake_graph.ainvoke = AsyncMock()

    with patch(
        ("app.api.dependencies.agent.create_user_shopping_graph"),
        return_value=fake_graph,
    ):
        response = client.post(
            "/api/v1/chat",
            json={
                "message": "请使用我的衣橱生成通勤搭配",
            },
        )

    assert response.status_code == 422

    # 缺少身份时不能执行可能读取用户衣橱的工作流
    fake_graph.ainvoke.assert_not_awaited()


def test_chat_returns_structured_configuration_error() -> None:
    """验证 LLM 配置缺失时返回统一错误响应。"""

    # 模拟 Agent 服务在创建工作流时抛出配置异常
    with patch(
        ("app.api.dependencies.agent.create_user_shopping_graph"),
        side_effect=ConfigurationError("缺少 LLM_API_KEY 配置"),
    ):
        response = client.post(
            "/api/v1/chat",
            headers={
                "X-User-ID": "user-001",
            },
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
        ("app.api.dependencies.agent.create_user_shopping_graph"),
        return_value=fake_graph,
    ):
        response = client.post(
            "/api/v1/chat",
            headers={
                "X-User-ID": "user-001",
            },
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
    assert graph_config["configurable"]["thread_id"] == (
        f"user:user-001:conversation:{conversation_id}"
    )


def test_delete_conversation_removes_current_user_state() -> None:
    """验证用户可以幂等删除自己的短期会话状态。"""

    delete_state = AsyncMock()

    with patch(
        "app.api.routers.chat.delete_conversation_state",
        delete_state,
    ):
        response = client.delete(
            "/api/v1/chat/conversation-001",
            headers={"X-User-ID": "user-001"},
        )

    assert response.status_code == 204
    assert response.content == b""
    delete_state.assert_awaited_once_with(
        user_id="user-001",
        conversation_id="conversation-001",
    )


def test_delete_conversation_requires_current_user() -> None:
    """验证匿名请求不能删除任何短期会话。"""

    delete_state = AsyncMock()

    with patch(
        "app.api.routers.chat.delete_conversation_state",
        delete_state,
    ):
        response = client.delete(
            "/api/v1/chat/conversation-001",
        )

    assert response.status_code == 422
    delete_state.assert_not_awaited()


def test_delete_conversation_rejects_oversized_id() -> None:
    """验证会话 ID 继续遵守聊天请求中的 100 字符上限。"""

    delete_state = AsyncMock()

    with patch(
        "app.api.routers.chat.delete_conversation_state",
        delete_state,
    ):
        response = client.delete(
            f"/api/v1/chat/{'x' * 101}",
            headers={"X-User-ID": "user-001"},
        )

    assert response.status_code == 422
    delete_state.assert_not_awaited()


def test_chat_returns_structured_outfit_when_graph_provides_one() -> None:
    """验证聊天接口能够返回 Graph 生成的结构化 Outfit。"""

    recommendation = OutfitRecommendation(
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
                reason="透气并适合通勤",
            ),
            OutfitItem(
                role="鞋履",
                name="黑色乐福鞋",
                source="recommendation",
                reason="补充通勤所需的利落鞋履",
            ),
        ],
        recommendation_reason="使用当前衣橱中的透气上装。",
        wardrobe_gaps=[
            WardrobeGap(
                role="鞋履",
                suggested_item="黑色乐福鞋",
                reason="当前衣橱结果中缺少通勤鞋履",
            ),
        ],
    )

    fake_graph = Mock()
    fake_graph.ainvoke = AsyncMock(
        return_value={
            "messages": [
                AIMessage(
                    content="我整理了一套夏季通勤搭配。",
                ),
            ],
            "outfit_recommendation": recommendation,
            "outfit_feasibility_report": (
                OutfitFeasibilityReport(
                    is_executable=True,
                    issues=(
                        OutfitFeasibilityIssue(
                            code=(OutfitIssueCode.PRECIPITATION_RISK),
                            severity=(OutfitIssueSeverity.WARNING),
                            message="建议补充雨具。",
                        ),
                    ),
                )
            ),
        },
    )

    with patch(
        ("app.api.dependencies.agent.create_user_shopping_graph"),
        return_value=fake_graph,
    ):
        response = client.post(
            "/api/v1/chat",
            headers={
                "X-User-ID": "user-001",
            },
            json={
                "message": "请用我的衣橱搭配夏季通勤服装",
            },
        )

    assert response.status_code == 200

    response_data = response.json()
    assert response_data["outfit"]["name"] == ("夏季通勤搭配")
    assert response_data["outfit"]["items"][0] == {
        "role": "上装",
        "name": "浅蓝色亚麻衬衫",
        "source": "wardrobe",
        "source_reference_id": "shirt-001",
        "reason": "透气并适合通勤",
    }
    assert response_data["outfit"]["wardrobe_gaps"][0]["suggested_item"] == "黑色乐福鞋"
    assert response_data["outfit_issues"] == [
        {
            "code": "precipitation_risk",
            "severity": "warning",
            "message": "建议补充雨具。",
            "item_reference_id": None,
        },
    ]


def test_chat_returns_structured_outfit_gap() -> None:
    """验证无法组成完整穿搭时 API 返回缺口而不是虚构 Outfit。"""

    gap = OutfitGapReport(
        missing_roles=(
            CoreOutfitRole.LOWER,
            CoreOutfitRole.FOOTWEAR,
        ),
        gaps=(
            WardrobeGap(
                role="下装",
                suggested_item="适合通勤的下装",
                reason="当前可用衣橱没有下装。",
            ),
            WardrobeGap(
                role="鞋履",
                suggested_item="适合通勤的鞋履",
                reason="当前可用衣橱没有鞋履。",
            ),
        ),
        shopping_search_allowed=False,
        next_actions=(
            OutfitGapNextAction.ADD_WARDROBE_ITEMS,
            OutfitGapNextAction.ADJUST_REQUIREMENTS,
        ),
        reason="当前真实候选不足以组成完整穿搭。",
    )
    fake_graph = Mock()
    fake_graph.ainvoke = AsyncMock(
        return_value={
            "messages": [
                AIMessage(
                    content=("当前衣橱缺少下装和鞋履，本轮不会自动查询商品。"),
                ),
            ],
            "outfit_recommendation": None,
            "outfit_gap_report": gap,
        },
    )

    with patch(
        ("app.api.dependencies.agent.create_user_shopping_graph"),
        return_value=fake_graph,
    ):
        response = client.post(
            "/api/v1/chat",
            headers={"X-User-ID": "user-001"},
            json={
                "message": "用我的衣橱搭配通勤服装",
            },
        )

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["outfit"] is None
    assert response_data["outfit_gap"]["missing_roles"] == ["下装", "鞋履"]
    assert response_data["outfit_gap"]["shopping_search_allowed"] is False
    assert "search_products" not in response_data["outfit_gap"]["next_actions"]
    assert response_data["outfit_issues"] == []


def test_chat_passes_user_provided_weather_to_graph() -> None:
    """验证结构化天气只作为当前轮状态传给 Agent。"""

    fake_graph = Mock()
    fake_graph.ainvoke = AsyncMock(
        return_value={
            "messages": [
                AIMessage(
                    content="建议穿透气衣物并携带雨具。",
                ),
            ],
        },
    )

    with patch(
        ("app.api.dependencies.agent.create_user_shopping_graph"),
        return_value=fake_graph,
    ):
        response = client.post(
            "/api/v1/chat",
            headers={
                "X-User-ID": "user-001",
            },
            json={
                "message": "明天通勤怎么穿？",
                "weather": {
                    "location": "上海",
                    "target_date": "2026-08-01",
                    "condition": "阵雨",
                    "temperature_min_c": 26,
                    "temperature_max_c": 33,
                    "precipitation_probability": 70,
                },
            },
        )

    assert response.status_code == 200
    input_state = fake_graph.ainvoke.call_args.args[0]
    weather = input_state["weather_context"]
    assert weather.location == "上海"
    assert weather.target_date.isoformat() == ("2026-08-01")
    assert weather.source.value == "user_provided"


def test_chat_rejects_invalid_weather_before_graph() -> None:
    """验证无事实或温度范围错误的天气请求返回 422。"""

    fake_graph = Mock()
    fake_graph.ainvoke = AsyncMock()

    with patch(
        ("app.api.dependencies.agent.create_user_shopping_graph"),
        return_value=fake_graph,
    ):
        response = client.post(
            "/api/v1/chat",
            headers={
                "X-User-ID": "user-001",
            },
            json={
                "message": "明天怎么穿？",
                "weather": {
                    "location": "上海",
                    "target_date": "2026-08-01",
                    "temperature_min_c": 35,
                    "temperature_max_c": 25,
                },
            },
        )

    assert response.status_code == 422
    fake_graph.ainvoke.assert_not_awaited()


def test_chat_returns_weather_snapshot_from_weather_tool() -> None:
    """验证天气工具结果会以结构化快照返回给前端。"""

    fake_graph = Mock()
    fake_graph.ainvoke = AsyncMock(
        return_value={
            "messages": [
                ToolMessage(
                    name="get_weather",
                    tool_call_id="weather-call-1",
                    content=json.dumps(
                        [
                            {
                                "location": "上海",
                                "target_date": "2026-08-09",
                                "condition": "晴",
                                "temperature_min_c": 27,
                                "temperature_max_c": 34,
                                "feels_like_c": 36,
                                "precipitation_probability": 10,
                                "humidity_percent": 70,
                                "wind_speed_kph": 12,
                                "source": "api",
                            },
                        ],
                        ensure_ascii=False,
                    ),
                ),
                AIMessage(content="今天适合穿透气的浅色衣物。"),
            ],
        },
    )

    with patch(
        "app.api.dependencies.agent.create_user_shopping_graph",
        return_value=fake_graph,
    ):
        response = client.post(
            "/api/v1/chat",
            headers={"X-User-ID": "user-001"},
            json={"message": "查询上海天气"},
        )

    assert response.status_code == 200
    assert response.json()["weather"] == {
        "location": "上海",
        "target_date": "2026-08-09",
        "condition": "晴",
        "temperature_min_c": 27.0,
        "temperature_max_c": 34.0,
        "feels_like_c": 36.0,
        "precipitation_probability": 10,
        "humidity_percent": 70,
        "wind_speed_kph": 12.0,
        "source": "api",
        "updated_at": None,
    }


def test_chat_stream_returns_progress_and_complete_events() -> None:
    """验证流式聊天接口会先推送进度，最后推送完整响应。"""

    fake_graph = Mock()

    async def fake_stream(*args: object, **kwargs: object):
        del args, kwargs
        yield {
            "messages": [
                AIMessage(content="流式回复"),
            ],
        }

    fake_graph.astream = fake_stream

    with patch(
        "app.api.dependencies.agent.create_user_shopping_graph",
        return_value=fake_graph,
    ):
        response = client.post(
            "/api/v1/chat/stream",
            headers={"X-User-ID": "user-001"},
            json={"message": "给我一套通勤穿搭"},
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert '"type": "status"' in response.text
    assert '"type": "complete"' in response.text
    assert '"message": "流式回复"' in response.text
