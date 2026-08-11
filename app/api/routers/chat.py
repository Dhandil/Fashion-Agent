import json
import logging
from collections.abc import Mapping
from typing import Annotated, Any, cast
from uuid import uuid4

from fastapi import APIRouter, Path, Response
from fastapi.responses import StreamingResponse
from langchain_core.messages import AnyMessage, HumanMessage
from langchain_core.runnables import RunnableConfig

from app.agents.context import get_current_turn_tool_records
from app.agents.state.shopping import ShoppingAgentState
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
from app.services.conversation import (
    delete_conversation_state,
    prune_conversation_checkpoints,
)

# 创建聊天接口路由
router = APIRouter(
    prefix="/chat",
    tags=["chat"],
)
logger = logging.getLogger(__name__)


def _build_conversation_context(
    request: ChatRequest,
    current_user_id: str,
) -> tuple[str, str, WeatherContext | None, RunnableConfig]:
    """构造会话 ID、线程 ID、请求天气和 LangGraph 配置。"""

    conversation_id = request.conversation_id or str(uuid4())
    thread_id = build_conversation_thread_id(
        user_id=current_user_id,
        conversation_id=conversation_id,
    )
    weather_context = (
        WeatherContext(
            **request.weather.model_dump(),
            source=WeatherDataSource.USER_PROVIDED,
        )
        if request.weather is not None
        else None
    )
    config: RunnableConfig = {
        "configurable": {"thread_id": thread_id},
        "metadata": {"request_id": get_request_id()},
    }
    return conversation_id, thread_id, weather_context, config


def _build_graph_input(
    request: ChatRequest,
    weather_context: WeatherContext | None,
) -> ShoppingAgentState:
    """将 HTTP 请求转换成工作流输入状态。"""

    return {
        "messages": [HumanMessage(content=request.message)],
        # 每轮都明确写入天气；None 会清除 Checkpointer 中的过期天气。
        "weather_context": weather_context,
        "weather_query": (
            request.weather_query.model_dump(mode="json", exclude_none=True)
            if request.weather_query is not None
            else None
        ),
        # 衣橱优先是本轮请求选项，不依赖对话历史隐式猜测。
        "wardrobe_preference_requested": request.wardrobe_preferred,
    }


def _extract_weather_context(result: Mapping[str, Any]) -> WeatherContext | None:
    """从最终状态或本轮天气工具消息中提取结构化天气。"""

    provided_weather = result.get("weather_context")
    if provided_weather is not None:
        try:
            return WeatherContext.model_validate(provided_weather)
        except (TypeError, ValueError):
            pass

    messages = result.get("messages", [])
    if not isinstance(messages, list):
        return None
    records = get_current_turn_tool_records(
        cast(list[AnyMessage], messages),
        "get_weather",
    )
    for record in reversed(records):
        try:
            return WeatherContext.model_validate(record)
        except (TypeError, ValueError):
            continue
    return None


def _build_chat_response(
    result: Mapping[str, Any],
    conversation_id: str,
) -> ChatResponse:
    """把 Agent 最终状态转换成统一的聊天响应。"""

    knowledge_sources = result.get("knowledge_sources", [])
    outfit_recommendation = result.get("outfit_recommendation")
    outfit_gap_report = result.get("outfit_gap_report")
    feasibility_report = result.get("outfit_feasibility_report")
    messages = result.get("messages", [])
    if not isinstance(messages, list) or not messages:
        raise ValueError("Agent 工作流没有返回消息")
    last_message = messages[-1]
    issues = (
        list(feasibility_report.issues)
        if feasibility_report is not None
        else []
    )
    return ChatResponse(
        conversation_id=conversation_id,
        message=str(last_message.content),
        weather=_extract_weather_context(result),
        outfit=outfit_recommendation,
        outfit_gap=outfit_gap_report,
        sources=list(knowledge_sources),
        outfit_issues=issues,
    )


def _sse_event(payload: Mapping[str, Any]) -> str:
    """将字典编码成前端可解析的 Server-Sent Event。"""

    return f"data: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"


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

    # 首次对话生成新 ID，后续对话继续使用客户端传入的 ID。
    conversation_id, _thread_id, weather_context, graph_config = (
        _build_conversation_context(request, current_user.user_id)
    )
    anonymous_user_id = anonymize_identifier(
        current_user.user_id,
    )
    anonymous_conversation_id = anonymize_identifier(
        conversation_id,
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
            _build_graph_input(request, weather_context),
            config=graph_config,
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
                len(feasibility_report.issues) if feasibility_report is not None else 0
            ),
        )

    # 最新状态已经完整写入后再裁剪旧快照；维护失败不会覆盖本次成功回复。
    await prune_conversation_checkpoints(
        user_id=current_user.user_id,
        conversation_id=conversation_id,
    )

    # 将 Agent 消息转换成 API 响应，并附带本轮天气快照。
    return _build_chat_response(result, conversation_id)


@router.post(
    "/stream",
    response_class=StreamingResponse,
    summary="以事件流方式与个人穿搭助手聊天",
)
async def chat_stream(
    request: ChatRequest,
    current_user: CurrentUserDependency,
    graph: RequestShoppingGraph,
) -> StreamingResponse:
    """逐步推送 Agent 工作阶段，最后发送完整聊天响应。"""

    conversation_id, _thread_id, weather_context, graph_config = (
        _build_conversation_context(request, current_user.user_id)
    )
    anonymous_user_id = anonymize_identifier(current_user.user_id)
    anonymous_conversation_id = anonymize_identifier(conversation_id)

    async def event_generator() -> Any:
        latest_result: Mapping[str, Any] | None = None
        try:
            log_event(
                logger,
                "agent.graph.started",
                conversation_is_new=request.conversation_id is None,
                has_weather=weather_context is not None,
                streaming=True,
                anonymous_user_id=anonymous_user_id,
                anonymous_conversation_id=anonymous_conversation_id,
            )
            yield _sse_event(
                {
                    "type": "status",
                    "stage": "analyzing",
                    "conversation_id": conversation_id,
                },
            )

            with observe_operation(
                logger,
                "agent.graph",
                anonymous_user_id=anonymous_user_id,
                anonymous_conversation_id=anonymous_conversation_id,
            ) as graph_observation:
                async for state in graph.astream(
                    _build_graph_input(request, weather_context),
                    config=graph_config,
                    stream_mode="values",
                ):
                    if isinstance(state, Mapping):
                        latest_result = cast(Mapping[str, Any], state)
                    yield _sse_event(
                        {
                            "type": "status",
                            "stage": "working",
                        },
                    )

                if latest_result is None:
                    raise ValueError("Agent 工作流没有产生最终状态")
                knowledge_sources = latest_result.get("knowledge_sources", [])
                feasibility_report = latest_result.get(
                    "outfit_feasibility_report",
                )
                graph_observation.add_fields(
                    source_count=len(knowledge_sources),
                    has_outfit=(
                        latest_result.get("outfit_recommendation") is not None
                    ),
                    has_outfit_gap=(
                        latest_result.get("outfit_gap_report") is not None
                    ),
                    outfit_issue_count=(
                        len(feasibility_report.issues)
                        if feasibility_report is not None
                        else 0
                    ),
                )

            await prune_conversation_checkpoints(
                user_id=current_user.user_id,
                conversation_id=conversation_id,
            )
            response = _build_chat_response(latest_result, conversation_id)
            log_event(
                logger,
                "agent.graph.completed",
                streaming=True,
                anonymous_user_id=anonymous_user_id,
                anonymous_conversation_id=anonymous_conversation_id,
                has_weather=response.weather is not None,
            )
            yield _sse_event(
                {
                    "type": "complete",
                    "response": response.model_dump(mode="json"),
                },
            )
        except Exception as exc:
            logger.exception(
                "流式 Agent 工作流失败",
                extra={"conversation_id": anonymous_conversation_id},
            )
            yield _sse_event(
                {
                    "type": "error",
                    "code": "agent_error",
                    "message": "助手暂时无法完成这次回答，请稍后重试。",
                    "error_type": type(exc).__name__,
                },
            )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
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
