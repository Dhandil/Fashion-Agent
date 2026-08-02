import logging
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Path, Response
from langchain_core.messages import HumanMessage

from app.api.dependencies.agent import (
    RequestShoppingGraph,
)
from app.api.dependencies.identity import (
    CurrentUserDependency,
)
from app.api.schemas.chat import ChatRequest, ChatResponse
from app.core.observability import (
    anonymize_identifier,
    log_event,
    observe_operation,
)
from app.core.request_context import get_request_id
from app.domain.entities.weather import (
    WeatherContext,
    WeatherDataSource,
)
from app.memory.short_term.thread import build_conversation_thread_id
from app.services.conversation import delete_conversation_state

# 创建聊天接口路由
router = APIRouter(
    prefix="/chat",
    tags=["chat"],
)
logger = logging.getLogger(__name__)


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
    thread_id = build_conversation_thread_id(
        user_id=current_user.user_id,
        conversation_id=conversation_id,
    )
    anonymous_user_id = anonymize_identifier(
        current_user.user_id,
    )
    anonymous_conversation_id = anonymize_identifier(
        conversation_id,
    )

    weather_context = (
        WeatherContext(
            **request.weather.model_dump(),
            source=WeatherDataSource.USER_PROVIDED,
        )
        if request.weather is not None
        else None
    )

    log_event(
        logger,
        "agent.graph.started",
        conversation_is_new=request.conversation_id is None,
        has_weather=weather_context is not None,
        anonymous_user_id=anonymous_user_id,
        anonymous_conversation_id=(anonymous_conversation_id),
    )

    # 将 API 请求转换为 LangChain 消息并执行工作流
    with observe_operation(
        logger,
        "agent.graph",
        anonymous_user_id=anonymous_user_id,
        anonymous_conversation_id=(anonymous_conversation_id),
    ) as graph_observation:
        result = await graph.ainvoke(
            {
                "messages": [
                    HumanMessage(content=request.message),
                ],
                # 每轮都明确写入天气；None 会清除 Checkpointer 中的过期天气
                "weather_context": weather_context,
            },
            config={
                "configurable": {
                    "thread_id": thread_id,
                },
                # metadata 可被 LangGraph/LangSmith 等后续观测后端直接读取
                "metadata": {
                    "request_id": get_request_id(),
                },
            },
        )
        # 在计时结束前补充不含用户正文的业务结果。
        knowledge_sources = result.get(
            "knowledge_sources",
            [],
        )
        outfit_recommendation = result.get(
            "outfit_recommendation",
        )
        outfit_gap_report = result.get(
            "outfit_gap_report",
        )
        feasibility_report = result.get(
            "outfit_feasibility_report",
        )
        graph_observation.add_fields(
            source_count=len(knowledge_sources),
            has_outfit=(outfit_recommendation is not None),
            has_outfit_gap=(outfit_gap_report is not None),
            outfit_issue_count=(
                len(feasibility_report.issues)
                if feasibility_report is not None
                else 0
            ),
        )

    # 读取工作流最终状态中的最后一条消息
    last_message = result["messages"][-1]

    # 将 Agent 消息转换成 API 响应
    return ChatResponse(
        conversation_id=conversation_id,
        message=str(last_message.content),
        outfit=outfit_recommendation,
        outfit_gap=outfit_gap_report,
        sources=knowledge_sources,
        outfit_issues=(list(feasibility_report.issues) if feasibility_report is not None else []),
    )


@router.delete(
    "/{conversation_id}",
    status_code=204,
    summary="结束并删除当前用户的短期会话",
)
async def delete_conversation(
    conversation_id: Annotated[
        str,
        Path(min_length=1, max_length=100),
    ],
    current_user: CurrentUserDependency,
) -> Response:
    """幂等删除当前用户在 Checkpointer 中的完整会话状态。"""

    await delete_conversation_state(
        user_id=current_user.user_id,
        conversation_id=conversation_id,
    )
    log_event(
        logger,
        "agent.conversation.deleted",
        anonymous_user_id=anonymize_identifier(
            current_user.user_id,
        ),
        anonymous_conversation_id=anonymize_identifier(
            conversation_id,
        ),
    )
    return Response(status_code=204)
