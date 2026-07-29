"""Agent 工具路由测试。"""

from langchain_core.messages import AIMessage
from langgraph.graph import END

from app.agents.routing.tools import route_after_chat
from app.agents.state.shopping import ShoppingAgentState


def test_route_after_chat_routes_to_tools() -> None:
    """验证模型发起工具调用时进入工具节点。"""

    # 模拟模型生成一条包含商品搜索请求的消息
    state: ShoppingAgentState = {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "search_products",
                        "args": {
                            "query": "衬衫",
                        },
                        "id": "call-1",
                        "type": "tool_call",
                    },
                ],
            ),
        ],
    }

    # 存在 tool_calls 时应该进入 tools 节点
    assert route_after_chat(state) == "tools"


def test_route_after_chat_routes_to_end() -> None:
    """验证模型直接回答时结束当前工作流。"""

    # 模拟模型直接生成普通文本回复
    state: ShoppingAgentState = {
        "messages": [
            AIMessage(
                content="建议选择亚麻混纺衬衫。",
            ),
        ],
    }

    # 不存在工具调用时应该结束工作流
    assert route_after_chat(state) == END