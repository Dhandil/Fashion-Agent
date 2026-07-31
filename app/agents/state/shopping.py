from typing import Annotated, NotRequired, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

from app.domain.entities.outfit import (
    OutfitRecommendation,
)


class ShoppingAgentState(TypedDict):
    """购物 Agent 在工作流中共享的状态。"""

    # 保存用户、AI 和工具产生的消息
    # add_messages 负责把新消息追加到现有的消息列表
    messages: Annotated[list[AnyMessage], add_messages]

    # RAG 检索得到的知识上下文
    # 并非每次请求都必须存在，因此使用 NotRequired
    knowledge_context: NotRequired[str]

    # 本次 RAG 检索结果的来源文件
    knowledge_sources: NotRequired[list[str]]

    # Agent 生成的结构化穿搭推荐；普通问答时可以不存在
    outfit_recommendation: NotRequired[OutfitRecommendation | None]
