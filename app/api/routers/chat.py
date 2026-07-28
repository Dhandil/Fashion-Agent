from fastapi import APIRouter
from langchain_core.messages import HumanMessage

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
def chat(request: ChatRequest) -> ChatResponse:
    """将用户消息发给购物 Agent 并返回回复。"""

    # 获取已经装配并缓存的购物 Agent 工作流
    graph = get_shopping_graph()

    # 将 API 请求转换为 LangChain 消息并执行工作流
    result = graph.invoke(
        {
            "messages": [
                HumanMessage(content=request.message),
            ],
        }
    )

    # 读取工作流最终状态中的最后一条消息
    last_message = result["messages"][-1]

    # 将 Agent 消息转换成 API 响应
    return ChatResponse(
        message=str(last_message.content),
    )