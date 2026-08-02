"""真实 Agent 冒烟脚本的无网络测试。"""

import json

import httpx
import pytest

from scripts.smoke_agent import (
    AgentSmokeError,
    run_agent_smoke,
    validate_agent_payload,
)


def test_run_agent_smoke_posts_message_and_validates_sources() -> None:
    """验证脚本向隔离用户发送消息并保留知识来源。"""

    captured_request: httpx.Request | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_request
        captured_request = request
        return httpx.Response(
            status_code=200,
            content=json.dumps(
                {
                    "conversation_id": "conversation-001",
                    "message": "亚麻透气，但容易产生自然褶皱。",
                    "sources": ["knowledge-001::S01::0001"],
                },
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )

    result = run_agent_smoke(
        base_url="http://testserver",
        user_id="model-smoke-user",
        message="测试问题",
        timeout=1.0,
        transport=httpx.MockTransport(handler),
    )

    assert captured_request is not None
    assert captured_request.method == "POST"
    assert captured_request.headers["X-User-ID"] == (
        "model-smoke-user"
    )
    assert json.loads(captured_request.content) == {
        "message": "测试问题",
    }
    assert result.conversation_id == "conversation-001"
    assert result.sources == ("knowledge-001::S01::0001",)


def test_validate_agent_payload_requires_rag_sources() -> None:
    """验证没有知识来源的回答不能冒充 RAG 链路成功。"""

    with pytest.raises(
        AgentSmokeError,
        match="RAG 来源",
    ):
        validate_agent_payload(
            {
                "conversation_id": "conversation-001",
                "message": "普通回答",
                "sources": [],
            },
        )
