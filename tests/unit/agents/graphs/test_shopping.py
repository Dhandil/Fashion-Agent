from unittest.mock import Mock

from langchain_core.documents import Document
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.retrievers import BaseRetriever
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver

from app.agents.graphs.shopping import create_shopping_graph


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
