"""工具权限拒绝节点测试。"""

from langchain_core.messages import AIMessage

from app.agents.nodes.reject_tools import (
    reject_disallowed_tool_calls,
)
from app.agents.schemas.requirements import (
    OutfitRequirementAnalysis,
    RequestIntent,
)


def test_reject_tool_node_returns_protocol_error_message() -> None:
    """验证拒绝节点会为模型的 Tool Call 补齐错误结果。"""

    result = reject_disallowed_tool_calls(
        {
            "messages": [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "search_products",
                            "args": {"query": "衬衫"},
                            "id": "product-call-1",
                            "type": "tool_call",
                        },
                    ],
                ),
            ],
            "requirement_analysis": (
                OutfitRequirementAnalysis(
                    intent=RequestIntent.OUTFIT,
                )
            ),
        },
    )

    tool_message = result["messages"][0]
    assert tool_message.tool_call_id == "product-call-1"
    assert tool_message.status == "error"
    assert "不允许调用" in tool_message.content
    assert result["tool_policy_rejection_count"] == 1
