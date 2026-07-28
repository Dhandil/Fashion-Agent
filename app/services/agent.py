from functools import lru_cache

from langgraph.graph.state import CompiledStateGraph

from app.agents.graphs.shopping import create_shopping_graph
from app.llm.providers.openai_compatible import create_chat_model


@lru_cache
def get_shopping_graph() -> CompiledStateGraph:
    """创建并缓存购物 Agent 工作流。"""

    # 根据环境配置创建聊天模型
    model = create_chat_model()

    # 将模型注入购物工作流并返回编译后的图
    return create_shopping_graph(model)