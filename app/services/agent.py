"""Fashion Agent 共享资源与请求级工作流装配。"""

from dataclasses import dataclass
from functools import lru_cache

from langchain_core.language_models import BaseChatModel
from langchain_core.retrievers import BaseRetriever
from langgraph.checkpoint.base import BaseCheckpointSaver

from app.agents.graphs.shopping import (
    ShoppingGraph,
    create_shopping_graph,
)
from app.domain.repositories.wardrobe import (
    WardrobeRepository,
)
from app.llm.providers.openai_compatible import create_chat_model
from app.memory.short_term.checkpointer import get_short_term_checkpointer
from app.rag.retrievers.provider import get_knowledge_retriever
from app.tools.registry.provider import (
    create_request_tool_registry,
)


@dataclass(
    frozen=True,
    slots=True,
)
class ShoppingAgentRuntime:
    """可以跨请求安全复用的 Agent 运行资源。"""

    model: BaseChatModel
    checkpointer: BaseCheckpointSaver[str]
    retriever: BaseRetriever


@lru_cache
def get_shopping_agent_runtime() -> ShoppingAgentRuntime:
    """创建并缓存不包含用户或数据库 Session 的共享资源。"""

    return ShoppingAgentRuntime(
        model=create_chat_model(),
        checkpointer=get_short_term_checkpointer(),
        retriever=get_knowledge_retriever(),
    )


def create_user_shopping_graph(
    wardrobe_repository: WardrobeRepository,
    user_id: str,
) -> ShoppingGraph:
    """为当前用户创建绑定请求级衣橱工具的工作流。"""

    # 模型、Retriever 和 Checkpointer 不包含请求级数据库状态
    runtime = get_shopping_agent_runtime()

    # 该注册表及衣橱工具只在当前请求中使用，不能加入全局缓存
    request_tool_registry = create_request_tool_registry(
        wardrobe_repository=wardrobe_repository,
        user_id=user_id,
    )

    return create_shopping_graph(
        model=runtime.model,
        checkpointer=runtime.checkpointer,
        retriever=runtime.retriever,
        tools=request_tool_registry.list_tools(),
    )
