from collections.abc import Sequence
from typing import cast

from langchain_core.language_models import BaseChatModel
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.base import BaseCheckpointSaver
from langchain_core.retrievers import BaseRetriever
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.prebuilt import ToolNode

from app.agents.nodes.chat import create_chat_node
from app.agents.state.shopping import ShoppingAgentState
from app.agents.nodes.retrieve_knowledge import (
    create_retrieve_knowledge_node,
)
from app.agents.routing.tools import route_after_chat

def create_shopping_graph(
    model: BaseChatModel,
    checkpointer: BaseCheckpointSaver | None = None,
    retriever: BaseRetriever | None = None,
    tools: Sequence[BaseTool] | None = None,
) -> CompiledStateGraph:
    """创建并编译购物 Agent 工作流。"""

    # 创建以 ShoppingAgentState 为共享状态的图构建器
    graph_builder = StateGraph(ShoppingAgentState)

    # 提供工具时，将工具定义绑定到聊天模型
    if tools:
        tool_enabled_model = cast(
            BaseChatModel,
            model.bind_tools(tools),
        )
    else:
        tool_enabled_model = model

    # 创建使用当前模型的聊天节点
    chat_node = create_chat_node(tool_enabled_model)

    # 将聊天节点注册到图中，节点名称为 chat
    graph_builder.add_node("chat", chat_node)

    # 提供 Retriever 时，先检索知识再调用聊天模型
    if retriever is not None:
        retrieve_knowledge_node = create_retrieve_knowledge_node(
            retriever,
        )

        graph_builder.add_node(
            "retrieve_knowledge",
            retrieve_knowledge_node,
        )
        graph_builder.add_edge(
            START,
            "retrieve_knowledge",
        )
        graph_builder.add_edge(
            "retrieve_knowledge",
            "chat",
        )
    else:
        # 不提供 Retriever 时保持原来的单节点工作流
        graph_builder.add_edge(
            START,
            "chat",
        )

    # 提供工具时，创建工具执行节点和循环路由
    if tools:
        graph_builder.add_node(
            "tools",
            ToolNode(list(tools)),
        )

        # 根据模型回复判断执行工具还是结束
        graph_builder.add_conditional_edges(
            "chat",
            route_after_chat,
            {
                "tools": "tools",
                END: END,
            },
        )

        # 工具执行完成后回到聊天节点，让模型整理最终回答
        graph_builder.add_edge(
            "tools",
            "chat",
        )
    else:
        # 没有提供工具时，聊天节点执行后直接结束
        graph_builder.add_edge(
            "chat",
            END,
        )

    # 编译后返回可以执行的工作流
    return graph_builder.compile(
        checkpointer=checkpointer,
    )