from fastapi import APIRouter
from langchain_core.messages import HumanMessage
from uuid import uuid4

from app.api.schemas.chat import ChatRequest, ChatResponse
from app.services.agent import get_shopping_graph


# 创建聊天接口路由
router = APIRouter(
    prefix="/chat",
    tags=["chat"],
)


@router.post(
    "",
    response_model=ChatResponse,
    summary="与购物助手聊天",
)
async def chat(
    request: ChatRequest
) -> ChatResponse:
    """将用户消息发给购物 Agent 并返回回复。"""

    # 获取已经装配并缓存的购物 Agent 工作流
    graph = get_shopping_graph()

    # 首次对话生成新 ID，后续对话继续使用客户端传入的 ID
    conversation_id = request.conversation_id or str(uuid4())

    # 将 API 请求转换为 LangChain 消息并执行工作流
    result = await graph.ainvoke(
        {
            "messages": [
                HumanMessage(content=request.message),
            ],
        },
        config={
            "configurable": {
                "thread_id": conversation_id,
            },
        },
    )

    # 读取工作流最终状态中的最后一条消息
    last_message = result["messages"][-1]

    # 读取 RAG Node 保存的知识来源
    knowledge_sources = result.get(
        "knowledge_sources",
        [],
    )

    # 将 Agent 消息转换成 API 响应
    return ChatResponse(
        conversation_id=conversation_id,
        message=str(last_message.content),
        sources=knowledge_sources,
    )