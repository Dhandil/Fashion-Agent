from langchain_core.language_models import BaseChatModel
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.agents.nodes.chat import create_chat_node
from app.agents.state.shopping import ShoppingAgentState


def create_shopping_graph(
    model: BaseChatModel,
) -> CompiledStateGraph:
    """创建并编译购物 Agent 工作流。"""

    # 创建以 ShoppingAgentState 为共享状态的图构建器
    graph_builder = StateGraph(ShoppingAgentState)

    # 创建已经绑定模型的聊天节点
    chat_node = create_chat_node(model)

    # 将聊天节点注册到图中，节点名称为 chat
    graph_builder.add_node("chat", chat_node)

    # 定义工作流入口：从 START 进入 chat 节点
    graph_builder.add_edge(START, "chat")

    # 定义工作流出口：chat 节点完成后结束
    graph_builder.add_edge("chat", END)

    # 编译后返回可以执行的工作流
    return graph_builder.compile()