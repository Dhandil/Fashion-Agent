"""Agent 工具路由测试。"""

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    ToolMessage,
)
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


def test_route_after_chat_routes_to_outfit_generation() -> None:
    """验证当前轮查询衣橱后进入结构化生成节点。"""

    state: ShoppingAgentState = {
        "messages": [
            HumanMessage(
                content="请用我的衣橱生成一套通勤搭配",
            ),
            ToolMessage(
                name="search_wardrobe",
                tool_call_id="wardrobe-call-1",
                content="[]",
            ),
            AIMessage(
                content="我已经查看了你的衣橱。",
            ),
        ],
    }

    assert route_after_chat(state) == ("generate_outfit")


def test_route_after_chat_ignores_previous_turn_wardrobe_tool() -> None:
    """验证上一轮衣橱工具不会触发当前轮 Outfit。"""

    state: ShoppingAgentState = {
        "messages": [
            HumanMessage(
                content="请查看我的衣橱",
            ),
            ToolMessage(
                name="search_wardrobe",
                tool_call_id="wardrobe-call-1",
                content="[]",
            ),
            AIMessage(
                content="当前衣橱为空。",
            ),
            HumanMessage(
                content="亚麻应该怎样护理？",
            ),
            AIMessage(
                content="建议按照洗涤标签低温清洗。",
            ),
        ],
    }

    assert route_after_chat(state) == END


def test_route_after_chat_ignores_failed_wardrobe_tool() -> None:
    """验证衣橱工具失败时不生成缺少可靠依据的 Outfit。"""

    state: ShoppingAgentState = {
        "messages": [
            HumanMessage(
                content="请用我的衣橱生成一套通勤搭配",
            ),
            ToolMessage(
                name="search_wardrobe",
                tool_call_id="wardrobe-call-1",
                content="数据库暂时不可用",
                status="error",
            ),
            AIMessage(
                content="暂时无法读取你的衣橱，请稍后再试。",
            ),
        ],
    }

    assert route_after_chat(state) == END
