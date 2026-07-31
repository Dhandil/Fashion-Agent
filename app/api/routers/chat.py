from uuid import uuid4

from fastapi import APIRouter
from langchain_core.messages import HumanMessage

from app.api.dependencies.agent import (
    RequestShoppingGraph,
)
from app.api.dependencies.identity import (
    CurrentUserDependency,
)
from app.api.schemas.chat import ChatRequest, ChatResponse

# 创建聊天接口路由
router = APIRouter(
    prefix="/chat",
    tags=["chat"],
)


@router.post(
    "",
    response_model=ChatResponse,
    summary="与个人穿搭助手聊天",
)
async def chat(
    request: ChatRequest,
    current_user: CurrentUserDependency,
    graph: RequestShoppingGraph,
) -> ChatResponse:
    """将用户消息发给当前用户的 Fashion Agent 并返回回复。"""

    # 首次对话生成新 ID，后续对话继续使用客户端传入的 ID
    conversation_id = request.conversation_id or str(uuid4())

    # 用户 ID 加入 Checkpointer 的线程键，避免不同用户复用会话 ID
    thread_id = f"user:{current_user.user_id}:conversation:{conversation_id}"

    # 将 API 请求转换为 LangChain 消息并执行工作流
    result = await graph.ainvoke(
        {
            "messages": [
                HumanMessage(content=request.message),
            ],
            # 每轮请求先清空旧推荐，避免返回上一轮的 Outfit
            "outfit_recommendation": None,
        },
        config={
            "configurable": {
                "thread_id": thread_id,
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

    # 普通知识问答可能没有结构化穿搭推荐
    outfit_recommendation = result.get(
        "outfit_recommendation",
    )

    # 将 Agent 消息转换成 API 响应
    return ChatResponse(
        conversation_id=conversation_id,
        message=str(last_message.content),
        outfit=outfit_recommendation,
        sources=knowledge_sources,
    )
