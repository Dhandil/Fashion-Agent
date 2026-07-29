from functools import lru_cache

from langgraph.graph.state import CompiledStateGraph

from app.agents.graphs.shopping import create_shopping_graph
from app.llm.providers.openai_compatible import create_chat_model
from app.memory.short_term.checkpointer import get_short_term_checkpointer
from app.rag.retrievers.provider import (
    get_knowledge_retriever
)
from app.tools.registry.provider import get_tool_registry

@lru_cache
def get_shopping_graph() -> CompiledStateGraph:
    """创建并缓存购物 Agent 工作流。"""

    # 根据环境配置创建聊天模型
    model = create_chat_model()

    # 获取应用共享的短期记忆存储器
    checkpointer = get_short_term_checkpointer()

    # 获取服装知识检索器
    retriever = get_knowledge_retriever()

    # 获取项目统一维护的工具注册表
    tool_registry = get_tool_registry()

    # 取得所有允许购物 Agent 使用的工具
    tools = tool_registry.list_tools()

    # 将模型和 Checkpointer 注入购物工作流
    return create_shopping_graph(
        model=model,
        checkpointer=checkpointer,
        retriever=retriever,
        tools=tools,
    )