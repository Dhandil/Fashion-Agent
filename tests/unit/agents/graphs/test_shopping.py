import json
from unittest.mock import Mock

from langchain_core.documents import Document
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.retrievers import BaseRetriever
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver

from app.agents.graphs.shopping import create_shopping_graph
from app.agents.schemas.outfit import OutfitGenerationResult
from app.agents.schemas.requirements import (
    OutfitRequirementAnalysis,
    RequestIntent,
    RequirementField,
)
from app.domain.entities.outfit import (
    OutfitItem,
    OutfitRecommendation,
)


def test_shopping_graph_runs_chat_node() -> None:
    """验证购物工作流能够执行聊天节点并合并消息。"""

    # 创建假模型，避免调用真实 LLM
    model = Mock(spec=BaseChatModel)
    model.invoke.return_value = AIMessage(
        content="请告诉我你的预算",
    )

    # 创建并编译工作流
    graph = create_shopping_graph(model)

    # 使用用户消息作为工作流的初始状态
    result = graph.invoke(
        {
            "messages": [HumanMessage(content="我想买一件衬衫")],
        }
    )

    # 验证图执行过程中调用了一次模型
    assert model.invoke.call_count == 1

    # add_messages 应该八六用户消息并追加 AI 回复
    assert len(result["messages"]) == 2
    assert result["messages"][0].content == "我想买一件衬衫"
    assert result["messages"][1].content == "请告诉我你的预算"


def test_incomplete_requirement_skips_retrieval_and_chat_model() -> None:
    """验证信息不足时只执行确定性最小追问。"""

    model = Mock(spec=BaseChatModel)
    analysis_model = Mock()
    model.with_structured_output.return_value = analysis_model
    analysis_model.invoke.return_value = OutfitRequirementAnalysis(
        intent=RequestIntent.OUTFIT,
        is_sufficient=False,
        missing_fields=(
            RequirementField.SCENARIO,
            RequirementField.LOCATION,
        ),
    )
    retriever = Mock(spec=BaseRetriever)
    graph = create_shopping_graph(
        model=model,
        retriever=retriever,
    )

    result = graph.invoke(
        {
            "messages": [
                HumanMessage(content="帮我搭配"),
            ],
        },
    )

    retriever.invoke.assert_not_called()
    model.invoke.assert_not_called()
    assert "使用场景" in result["messages"][-1].content
    assert "地点" in result["messages"][-1].content


def test_shopping_graph_moves_previous_outfit_to_adjustment_baseline() -> None:
    """验证工作流每轮清空旧输出但保留结构化调整基线。"""

    model = Mock(spec=BaseChatModel)
    model.invoke.return_value = AIMessage(
        content="我会为你调整上衣。",
    )
    previous_outfit = OutfitRecommendation(
        name="原通勤搭配",
        scenario="通勤",
        items=(
            OutfitItem(
                role="上装",
                name="浅蓝色衬衫",
                source="wardrobe",
                source_reference_id="shirt-001",
            ),
        ),
        recommendation_reason="原方案。",
    )
    graph = create_shopping_graph(model)

    result = graph.invoke(
        {
            "messages": [
                HumanMessage(
                    content="换一件上衣",
                ),
            ],
            "outfit_recommendation": previous_outfit,
        },
    )

    assert result["outfit_recommendation"] is None
    assert result["previous_outfit_recommendation"] == previous_outfit


def test_shopping_graph_remembers_messages_in_same_thread() -> None:
    """验证同一个 thread_id 能够保留多轮对话历史。"""

    # 创建假模型，并为两次调用准备不同回复
    model = Mock(spec=BaseChatModel)
    model.invoke.side_effect = [
        AIMessage(content="请告诉我你的预算"),
        AIMessage(content="我会按照 300 元预算推荐"),
    ]

    # 每个测试使用独立的内存 Checkpointer
    checkpointer = InMemorySaver()
    graph = create_shopping_graph(
        model,
        checkpointer,
    )

    # 两轮请求使用相同的 thread_id
    config = {
        "configurable": {
            "thread_id": "test-thread",
        },
    }

    # 第一轮对话
    graph.invoke(
        {
            "messages": [
                HumanMessage(content="我想买一件衬衫"),
            ],
        },
        config=config,
    )

    # 第二轮对话
    result = graph.invoke(
        {
            "messages": [
                HumanMessage(content="预算 300 元"),
            ],
        },
        config=config,
    )

    # 第二轮结束后，State 应包含两轮用户消息和两轮 AI 回复
    assert len(result["messages"]) == 4
    assert result["messages"][0].content == "我想买一件衬衫"
    assert result["messages"][1].content == "请告诉我你的预算"
    assert result["messages"][2].content == "预算 300 元"
    assert result["messages"][3].content == "我会按照 300 元预算推荐"

    # 读取第二次模型调用收到的消息
    second_call_messages = model.invoke.call_args_list[1].args[0]

    # System Prompt 后面应该包含完整的两轮上下文
    assert second_call_messages[1].content == "我想买一件衬衫"
    assert second_call_messages[2].content == "请告诉我你的预算"
    assert second_call_messages[3].content == "预算 300 元"


def test_shopping_graph_persists_summary_for_omitted_turns() -> None:
    """验证退出模型窗口的旧轮次形成摘要并随同一线程保存。"""

    model = Mock(spec=BaseChatModel)
    model.invoke.side_effect = [
        AIMessage(content="第一轮回复"),
        AIMessage(content="第二轮回复"),
    ]
    graph = create_shopping_graph(
        model,
        InMemorySaver(),
        history_max_turns=1,
        history_max_chars=10_000,
    )
    config = {
        "configurable": {
            "thread_id": "summary-thread",
        },
    }

    graph.invoke(
        {
            "messages": [
                HumanMessage(content="第一轮用户要求"),
            ],
        },
        config=config,
    )
    result = graph.invoke(
        {
            "messages": [
                HumanMessage(content="第二轮用户要求"),
            ],
        },
        config=config,
    )

    summary = result["conversation_summary"]
    assert summary is not None
    assert "用户：第一轮用户要求" in summary.content
    assert "助手：第一轮回复" in summary.content

    second_call_messages = model.invoke.call_args_list[1].args[0]
    assert [message.content for message in second_call_messages[1:]] == ["第二轮用户要求"]


def test_separately_compiled_graphs_share_checkpointer_history() -> None:
    """验证请求级重新编译 Graph 后仍能恢复同一会话。"""

    model = Mock(spec=BaseChatModel)
    model.invoke.side_effect = [
        AIMessage(content="第一轮回复"),
        AIMessage(content="第二轮回复"),
    ]

    # 两个请求级 Graph 共享不包含数据库 Session 的 Checkpointer
    checkpointer = InMemorySaver()
    first_graph = create_shopping_graph(
        model=model,
        checkpointer=checkpointer,
    )
    second_graph = create_shopping_graph(
        model=model,
        checkpointer=checkpointer,
    )

    config = {
        "configurable": {
            "thread_id": "user:user-001:conversation:test-thread",
        },
    }

    first_graph.invoke(
        {
            "messages": [
                HumanMessage(content="第一轮问题"),
            ],
        },
        config=config,
    )
    result = second_graph.invoke(
        {
            "messages": [
                HumanMessage(content="第二轮问题"),
            ],
        },
        config=config,
    )

    # 新 Graph 应从共享 Checkpointer 中恢复第一轮消息
    assert [message.content for message in result["messages"]] == [
        "第一轮问题",
        "第一轮回复",
        "第二轮问题",
        "第二轮回复",
    ]


def test_shopping_graph_uses_retrieved_knowledge() -> None:
    """验证 RAG Graph 先检索知识再调用聊天模型。"""

    # 创建假 Retriever 并提供知识片段
    retriever = Mock(spec=BaseRetriever)
    retriever.invoke.return_value = [
        Document(
            page_content=("亚麻面料透气性和吸湿性较好，适合炎热天气穿着。"),
        ),
    ]

    # 创建假聊天模型
    model = Mock(spec=BaseChatModel)
    model.invoke.return_value = AIMessage(
        content="建议选择亚麻面料。",
    )

    # 创建启用 RAG 的工作流
    graph = create_shopping_graph(
        model=model,
        retriever=retriever,
    )

    # 执行工作流
    result = graph.invoke(
        {
            "messages": [
                HumanMessage(
                    content="夏天通勤适合什么面料？",
                ),
            ],
        }
    )

    # RAG Node 应使用用户问题执行检索
    retriever.invoke.assert_called_once_with(
        "夏天通勤适合什么面料？",
    )

    # 最终 State 应保存检索到的知识
    assert "亚麻面料透气性和吸湿性较好" in (result["knowledge_context"])

    # 读取 Chat Node 实际发送给模型的 System Message
    sent_messages = model.invoke.call_args.args[0]
    system_message = sent_messages[0]

    # System Message 应包含 RAG 知识
    assert "亚麻面料透气性和吸湿性较好" in (system_message.content)

    # Graph 应返回模型回复
    assert result["messages"][-1].content == ("建议选择亚麻面料。")


def test_shopping_graph_executes_tool_call() -> None:
    """验证工作流能够执行模型请求的工具并返回最终回答。"""

    # 用 Mock 记录商品搜索函数是否被执行
    search_function = Mock(
        return_value='[{"name": "亚麻通勤衬衫"}]',
    )

    @tool
    def search_products(query: str) -> str:
        """根据关键词搜索服装商品。"""

        # 测试工具内部调用可监控的假搜索函数
        return search_function(query)

    # 原始模型负责执行 bind_tools()
    model = Mock(spec=BaseChatModel)

    # 绑定工具后返回的模型负责实际生成消息
    tool_enabled_model = Mock(spec=BaseChatModel)
    model.bind_tools.return_value = tool_enabled_model

    # 第一次回复请求调用工具，第二次回复生成最终答案
    tool_enabled_model.invoke.side_effect = [
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "search_products",
                    "args": {
                        "query": "亚麻衬衫",
                    },
                    "id": "call-1",
                    "type": "tool_call",
                },
            ],
        ),
        AIMessage(
            content="推荐亚麻通勤衬衫。",
        ),
    ]

    # 创建启用商品搜索工具的工作流
    graph = create_shopping_graph(
        model=model,
        tools=[search_products],
    )

    # 执行一次用户请求
    result = graph.invoke(
        {
            "messages": [
                HumanMessage(
                    content="帮我找一件亚麻衬衫。",
                ),
            ],
        },
    )

    # 原始模型应该接收到工具定义
    model.bind_tools.assert_called_once()

    # 工作流应该使用模型提供的参数执行商品搜索
    search_function.assert_called_once_with(
        "亚麻衬衫",
    )

    # 模型会在工具执行前后各调用一次
    assert tool_enabled_model.invoke.call_count == 2

    # 第二次模型回复是工作流的最终结果
    assert result["messages"][-1].content == ("推荐亚麻通勤衬衫。")


def test_shopping_graph_corrects_invalid_outfit_once() -> None:
    """验证完整工作流只修正一次，并对修正结果重新执行检查。"""

    wardrobe_records = [
        {
            "wardrobe_item_id": item_id,
            "name": name,
            "status": "available",
        }
        for item_id, name in (
            ("upper-001", "亚麻衬衫"),
            ("lower-001", "直筒长裤"),
            ("shoes-001", "乐福鞋"),
        )
    ]

    @tool
    def search_wardrobe(query: str) -> str:
        """根据穿搭需求查询当前可用衣物。"""

        return json.dumps(
            wardrobe_records,
            ensure_ascii=False,
        )

    original_outfit = OutfitRecommendation(
        name="不完整通勤方案",
        scenario="通勤",
        items=(
            OutfitItem(
                role="上装",
                name="亚麻衬衫",
                source="wardrobe",
                source_reference_id="upper-001",
            ),
        ),
        recommendation_reason="目前只有上装。",
    )
    corrected_outfit = OutfitRecommendation(
        name="完整通勤方案",
        scenario="通勤",
        items=(
            OutfitItem(
                role="上装",
                name="亚麻衬衫",
                source="wardrobe",
                source_reference_id="upper-001",
            ),
            OutfitItem(
                role="下装",
                name="直筒长裤",
                source="wardrobe",
                source_reference_id="lower-001",
            ),
            OutfitItem(
                role="鞋履",
                name="乐福鞋",
                source="wardrobe",
                source_reference_id="shoes-001",
            ),
        ),
        recommendation_reason="补齐通勤所需核心单品。",
    )

    # 三个结构化模型依次负责需求分析、初次生成和唯一一次修正。
    model = Mock(spec=BaseChatModel)
    analysis_model = Mock()
    generation_model = Mock()
    correction_model = Mock()
    model.with_structured_output.side_effect = [
        analysis_model,
        generation_model,
        correction_model,
    ]
    analysis_model.invoke.return_value = OutfitRequirementAnalysis(
        intent=RequestIntent.OUTFIT,
        scenario="通勤",
        needs_wardrobe=True,
    )
    generation_model.invoke.return_value = OutfitGenerationResult(outfit=original_outfit)
    correction_model.invoke.return_value = OutfitGenerationResult(outfit=corrected_outfit)

    tool_enabled_model = Mock(spec=BaseChatModel)
    model.bind_tools.return_value = tool_enabled_model
    tool_enabled_model.invoke.side_effect = [
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "search_wardrobe",
                    "args": {"query": "通勤"},
                    "id": "wardrobe-call-1",
                    "type": "tool_call",
                },
            ],
        ),
        AIMessage(content="正在整理通勤方案。"),
    ]

    graph = create_shopping_graph(
        model=model,
        tools=[search_wardrobe],
    )
    result = graph.invoke(
        {
            "messages": [
                HumanMessage(
                    content="用我的衣橱搭配一套通勤服装",
                ),
            ],
        },
    )

    assert generation_model.invoke.call_count == 1
    assert correction_model.invoke.call_count == 1
    assert result["outfit_correction_attempts"] == 1
    assert result["outfit_recommendation"] == corrected_outfit
    assert result["outfit_feasibility_report"].is_executable is True
