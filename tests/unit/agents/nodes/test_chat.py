from unittest.mock import Mock

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.agents.nodes.chat import create_chat_node
from app.agents.prompts.shopping import SHOPPING_ASSISTANT_SYSTEM_PROMPT
from app.agents.state.shopping import ShoppingAgentState


def test_chat_node_invokes_bound_model() -> None:
    """验证聊天节点会调用闭包中绑定的模型。"""

    # 创建一个符合 BaseChatModel 接口的假模型
    model = Mock(spec=BaseChatModel)

    # 指定假模型被调用后返回的 AI 消息
    model.invoke.return_value = AIMessage(content="请告诉我你的预算")

    # 创建节点，model 会被保存在闭包中
    chat_node = create_chat_node(model)

    # 模拟 LangGraph 传入的当前状态
    state: ShoppingAgentState = {
        "messages": [
            HumanMessage(content="我想买一件衬衫"),
        ],
    }

    # 执行节点，此时闭包中的 model 才会被调用
    result = chat_node(state)

    # 验证模型只被调用一次
    model.invoke.assert_called_once()

    # 取得调用 invoke() 时传入的消息列表
    sent_messages = model.invoke.call_args.args[0]

    # 第一条应该是购物助手系统提示词
    assert isinstance(sent_messages[0], SystemMessage)
    assert sent_messages[0].content == SHOPPING_ASSISTANT_SYSTEM_PROMPT

    # 第二条应该是用户消息
    assert isinstance(sent_messages[1], HumanMessage)
    assert sent_messages[1].content == "我想买一件衬衫"

    # 验证节点返回模型产生的新消息
    assert len(result["messages"]) == 1
    assert result["messages"][0].content == "请告诉我你的预算"


def test_chat_node_includes_knowledge_context() -> None:
    """验证 Chat Node 将 RAG 知识加入系统提示词。"""

    # 创建假模型和固定回复
    model = Mock(spec=BaseChatModel)
    model.invoke.return_value = AIMessage(
        content="建议选择亚麻面料。",
    )

    # 创建聊天节点
    chat_node = create_chat_node(model)

    # State 同时包含用户消息和 RAG 知识
    state: ShoppingAgentState = {
        "messages": [
            HumanMessage(
                content="夏天通勤适合什么面料？",
            ),
        ],
        "knowledge_context": (
            "亚麻面料透气性和吸湿性较好，"
            "适合炎热天气穿着。"
        ),
    }

    # 执行聊天节点
    chat_node(state)

    # 读取实际发送给模型的消息列表
    sent_messages = model.invoke.call_args.args[0]

    # 第一条消息应该仍然是 System Message
    system_message = sent_messages[0]
    assert isinstance(system_message, SystemMessage)

    # 固定购物助手规则应该继续存在
    assert SHOPPING_ASSISTANT_SYSTEM_PROMPT in (
        system_message.content
    )

    # RAG 检索知识应该被加入系统提示词
    assert "亚麻面料透气性和吸湿性较好" in (
        system_message.content
    )

    # 应包含要求模型优先依据资料的约束
    assert "请优先根据参考资料回答" in (
        system_message.content
    )


def test_chat_node_includes_confirmed_feedback_context() -> None:
    """验证 Chat Node 把历史反馈作为受约束的偏好数据。"""

    model = Mock(spec=BaseChatModel)
    model.invoke.return_value = AIMessage(
        content="这次会避开过于正式的搭配。",
    )
    chat_node = create_chat_node(model)
    state: ShoppingAgentState = {
        "messages": [
            HumanMessage(
                content="帮我搭配周末出游服装",
            ),
        ],
        "outfit_feedback_context": (
            "- 历史穿搭：正式通勤；"
            "用户态度：不喜欢；"
            "用户说明：不喜欢过于正式"
        ),
    }

    chat_node(state)

    system_message = model.invoke.call_args.args[0][0]
    assert "不喜欢过于正式" in system_message.content
    assert "只作为用户偏好数据" in (
        system_message.content
    )
    assert "当前用户明确提出的新需求优先" in (
        system_message.content
    )
