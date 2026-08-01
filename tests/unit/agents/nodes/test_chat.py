from unittest.mock import Mock

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.agents.nodes.chat import create_chat_node
from app.agents.prompts.shopping import SHOPPING_ASSISTANT_SYSTEM_PROMPT
from app.agents.state.shopping import ShoppingAgentState
from app.domain.entities.outfit import (
    OutfitItem,
    OutfitRecommendation,
)
from app.domain.entities.weather import WeatherContext


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
        "knowledge_context": ("亚麻面料透气性和吸湿性较好，适合炎热天气穿着。"),
    }

    # 执行聊天节点
    chat_node(state)

    # 读取实际发送给模型的消息列表
    sent_messages = model.invoke.call_args.args[0]

    # 第一条消息应该仍然是 System Message
    system_message = sent_messages[0]
    assert isinstance(system_message, SystemMessage)

    # 固定购物助手规则应该继续存在
    assert SHOPPING_ASSISTANT_SYSTEM_PROMPT in (system_message.content)

    # RAG 检索知识应该被加入系统提示词
    assert "亚麻面料透气性和吸湿性较好" in (system_message.content)

    # 应包含要求模型优先依据资料的约束
    assert "请优先根据参考资料回答" in (system_message.content)


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
            "- 历史穿搭：正式通勤；用户态度：不喜欢；用户说明：不喜欢过于正式"
        ),
    }

    chat_node(state)

    system_message = model.invoke.call_args.args[0][0]
    assert "不喜欢过于正式" in system_message.content
    assert "只作为用户偏好数据" in (system_message.content)
    assert "当前用户明确提出的新需求优先" in (system_message.content)


def test_chat_node_includes_explicit_style_profile() -> None:
    """验证明确维护的 Style Profile 高于历史反馈。"""

    model = Mock(spec=BaseChatModel)
    model.invoke.return_value = AIMessage(
        content="按照你的长期偏好搭配。",
    )
    chat_node = create_chat_node(model)
    state: ShoppingAgentState = {
        "messages": [
            HumanMessage(
                content="这次想尝试正式风格",
            ),
        ],
        "style_profile_context": ("- 喜欢的风格：休闲\n- 用户主动说明：平时不要过于正式"),
        "outfit_feedback_context": ("- 用户态度：喜欢；用户说明：喜欢简约"),
    }

    chat_node(state)

    system_message = model.invoke.call_args.args[0][0]
    assert "喜欢的风格：休闲" in (system_message.content)
    assert "应优先于历史反馈使用" in (system_message.content)
    assert "以当前需求为准" in (system_message.content)


def test_chat_node_includes_recent_outfits_as_soft_constraint() -> None:
    """验证近期 Outfit 只作为减少重复的软约束。"""

    model = Mock(spec=BaseChatModel)
    model.invoke.return_value = AIMessage(
        content="这次会优先更换一件主要单品。",
    )
    chat_node = create_chat_node(model)
    state: ShoppingAgentState = {
        "messages": [
            HumanMessage(
                content="再帮我搭配一套通勤服装",
            ),
        ],
        "recent_outfits_context": ("- 近期穿搭：清爽通勤；单品组合：上装：浅蓝色衬衫"),
    }

    chat_node(state)

    system_message = model.invoke.call_args.args[0][0]
    assert "清爽通勤" in system_message.content
    assert "减少短期内重复相同衣物组合" in (system_message.content)
    assert "可以合理复用近期单品" in (system_message.content)


def test_chat_node_includes_previous_outfit_for_adjustment() -> None:
    """验证上一套结构化 Outfit 会作为局部调整基线。"""

    model = Mock(spec=BaseChatModel)
    model.invoke.return_value = AIMessage(
        content="我会保留下装并更换上衣。",
    )
    chat_node = create_chat_node(model)
    previous_outfit = OutfitRecommendation(
        name="清爽通勤",
        scenario="通勤",
        items=(
            OutfitItem(
                role="上装",
                name="浅蓝色衬衫",
                source="wardrobe",
                source_reference_id="shirt-001",
            ),
        ),
        recommendation_reason="适合通勤。",
    )
    state: ShoppingAgentState = {
        "messages": [
            HumanMessage(
                content="换一件上衣",
            ),
        ],
        "previous_outfit_recommendation": (previous_outfit),
    }

    chat_node(state)

    system_message = model.invoke.call_args.args[0][0]
    assert "清爽通勤" in system_message.content
    assert "局部调整要求" in (system_message.content)
    assert "仍需重新查询当前可用衣橱" in (system_message.content)


def test_chat_node_includes_current_weather_context() -> None:
    """验证当前轮天气作为事实而不是系统指令加入提示词。"""

    model = Mock(spec=BaseChatModel)
    model.invoke.return_value = AIMessage(
        content="建议穿透气衣物并携带雨具。",
    )
    chat_node = create_chat_node(model)
    state: ShoppingAgentState = {
        "messages": [
            HumanMessage(
                content="明天通勤怎么穿？",
            ),
        ],
        "weather_context": WeatherContext(
            location="上海",
            target_date="2026-08-01",
            condition="阵雨",
            temperature_max_c=33,
            precipitation_probability=70,
            source="user_provided",
        ),
    }

    chat_node(state)

    system_message = model.invoke.call_args.args[0][0]
    assert '"location":"上海"' in (system_message.content)
    assert '"precipitation_probability":70' in (system_message.content)
    assert "不要补造缺失的实时天气" in (system_message.content)
    assert "高温或体感炎热" in (system_message.content)
    assert "明显降水风险" in (system_message.content)
