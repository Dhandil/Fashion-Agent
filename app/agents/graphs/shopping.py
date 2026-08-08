from collections.abc import Sequence
from typing import Any, TypeAlias, cast

from langchain_core.language_models import BaseChatModel
from langchain_core.retrievers import BaseRetriever
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode

from app.agents.context_package import (
    DEFAULT_CONTEXT_BUDGET_POLICY,
    ContextBudgetPolicy,
)
from app.agents.knowledge_context import (
    DEFAULT_KNOWLEDGE_CONTEXT_POLICY,
    KnowledgeContextPolicy,
)
from app.agents.nodes.analyze_requirements import (
    create_requirement_analysis_node,
)
from app.agents.nodes.chat import create_chat_node
from app.agents.nodes.clarify_requirements import (
    clarify_requirements,
)
from app.agents.nodes.correct_outfit import (
    create_outfit_correction_node,
)
from app.agents.nodes.generate_outfit import (
    create_outfit_generation_node,
)
from app.agents.nodes.load_outfit_feedback import (
    create_load_outfit_feedback_node,
)
from app.agents.nodes.load_recent_outfits import (
    create_load_recent_outfits_node,
)
from app.agents.nodes.load_style_profile import (
    create_load_style_profile_node,
)
from app.agents.nodes.prepare_turn import (
    create_prepare_turn_node,
)
from app.agents.nodes.reject_tools import (
    reject_disallowed_tool_calls,
)
from app.agents.nodes.resolve_weather import (
    create_weather_query_node,
)
from app.agents.nodes.retrieve_knowledge import (
    create_retrieve_knowledge_node,
)
from app.agents.nodes.validate_outfit import validate_outfit
from app.agents.routing.outfit_validation import (
    route_after_outfit_validation,
)
from app.agents.routing.requirements import (
    route_after_requirement_analysis,
)
from app.agents.routing.tools import route_after_chat
from app.agents.state.shopping import ShoppingAgentState
from app.domain.repositories.outfit import OutfitRepository
from app.domain.repositories.outfit_feedback import (
    OutfitFeedbackRepository,
)
from app.domain.repositories.style_profile import (
    StyleProfileRepository,
)
from app.memory.short_term.conversation_summary import (
    DEFAULT_SUMMARY_MAX_CHARS,
)
from app.memory.short_term.conversation_window import (
    DEFAULT_HISTORY_MAX_CHARS,
    DEFAULT_HISTORY_MAX_TURNS,
)

ShoppingGraph: TypeAlias = CompiledStateGraph[
    ShoppingAgentState,
    None,
    ShoppingAgentState,
    ShoppingAgentState,
]


def create_shopping_graph(
    model: BaseChatModel,
    checkpointer: BaseCheckpointSaver[str] | None = None,
    retriever: BaseRetriever | None = None,
    tools: Sequence[BaseTool] | None = None,
    outfit_repository: OutfitRepository | None = None,
    outfit_feedback_repository: (OutfitFeedbackRepository | None) = None,
    style_profile_repository: (StyleProfileRepository | None) = None,
    user_id: str | None = None,
    context_budget_policy: ContextBudgetPolicy = (DEFAULT_CONTEXT_BUDGET_POLICY),
    knowledge_context_policy: KnowledgeContextPolicy = (
        DEFAULT_KNOWLEDGE_CONTEXT_POLICY
    ),
    history_max_turns: int = DEFAULT_HISTORY_MAX_TURNS,
    history_max_chars: int = DEFAULT_HISTORY_MAX_CHARS,
    summary_max_chars: int = DEFAULT_SUMMARY_MAX_CHARS,
) -> ShoppingGraph:
    """创建并编译个人穿搭 Agent 工作流。"""

    feedback_dependencies = (
        outfit_repository,
        outfit_feedback_repository,
        user_id,
    )

    if any(dependency is not None for dependency in feedback_dependencies) and not all(
        dependency is not None for dependency in feedback_dependencies
    ):
        raise ValueError(
            "加载 Outfit 反馈需要同时提供两个仓库和 user_id",
        )

    if style_profile_repository is not None and user_id is None:
        raise ValueError(
            "加载 Style Profile 需要同时提供 user_id",
        )

    # 创建以 ShoppingAgentState 为共享状态的图构建器
    graph_builder = StateGraph(ShoppingAgentState)

    # 提供工具时，将工具定义绑定到聊天模型
    if tools:
        tool_enabled_model = cast(
            BaseChatModel,
            model.bind_tools(tools),
        )
    else:
        tool_enabled_model = model

    # 创建需求分析和聊天节点；分析模型不绑定业务工具，只输出路由状态
    requirement_analysis_node = create_requirement_analysis_node(model)
    graph_builder.add_node(
        "analyze_requirements",
        cast(Any, requirement_analysis_node),
    )

    chat_node = create_chat_node(
        tool_enabled_model,
        context_budget_policy=context_budget_policy,
        history_max_turns=history_max_turns,
        history_max_chars=history_max_chars,
        summary_max_chars=summary_max_chars,
    )

    # 将聊天节点注册到图中，节点名称为 chat
    # LangGraph 当前类型桩无法识别工厂返回的节点闭包，运行时接口是兼容的
    graph_builder.add_node(
        "chat",
        cast(Any, chat_node),
    )
    graph_builder.add_node(
        "clarify_requirements",
        cast(Any, clarify_requirements),
    )
    graph_builder.add_edge(
        "clarify_requirements",
        END,
    )

    # 每轮先保存上一套结构化推荐并清空本轮输出，避免返回过期 Outfit
    prepare_turn_node = create_prepare_turn_node()
    graph_builder.add_node(
        "prepare_turn",
        cast(Any, prepare_turn_node),
    )
    graph_builder.add_edge(
        START,
        "prepare_turn",
    )

    weather_tool = next(
        (tool for tool in tools or () if tool.name == "get_weather"),
        None,
    )
    graph_builder.add_node(
        "resolve_weather_query",
        cast(Any, create_weather_query_node(weather_tool)),
    )
    graph_builder.add_edge(
        "prepare_turn",
        "resolve_weather_query",
    )
    graph_builder.add_edge(
        "resolve_weather_query",
        "analyze_requirements",
    )

    # 个性化链路仅在需求充分且确实需要穿搭、衣橱或购物时执行。
    personalized_entry: str | None = None
    personalized_tail: str | None = None

    if style_profile_repository is not None and user_id is not None:
        load_style_profile_node = create_load_style_profile_node(
            repository=style_profile_repository,
            user_id=user_id,
        )
        style_profile_node_name = "load_style_profile"
        graph_builder.add_node(
            style_profile_node_name,
            cast(Any, load_style_profile_node),
        )
        personalized_entry = style_profile_node_name
        personalized_tail = style_profile_node_name

    if outfit_repository is not None and user_id is not None:
        load_recent_outfits_node = create_load_recent_outfits_node(
            repository=outfit_repository,
            user_id=user_id,
        )
        recent_outfits_node_name = "load_recent_outfits"
        graph_builder.add_node(
            recent_outfits_node_name,
            cast(Any, load_recent_outfits_node),
        )

        if personalized_tail is not None:
            graph_builder.add_edge(
                personalized_tail,
                recent_outfits_node_name,
            )

        personalized_entry = personalized_entry or recent_outfits_node_name
        personalized_tail = recent_outfits_node_name

    if (
        outfit_repository is not None
        and outfit_feedback_repository is not None
        and user_id is not None
    ):
        load_outfit_feedback_node = create_load_outfit_feedback_node(
            outfit_repository=outfit_repository,
            feedback_repository=(outfit_feedback_repository),
            user_id=user_id,
        )
        feedback_node_name = "load_outfit_feedback"
        graph_builder.add_node(
            feedback_node_name,
            cast(Any, load_outfit_feedback_node),
        )

        if personalized_tail is not None:
            graph_builder.add_edge(
                personalized_tail,
                feedback_node_name,
            )

        personalized_entry = personalized_entry or feedback_node_name
        personalized_tail = feedback_node_name

    # 知识问答可直接进入 Retriever；个性化请求则在用户数据之后检索。
    retrieval_node_name: str | None = None
    if retriever is not None:
        retrieve_knowledge_node = create_retrieve_knowledge_node(
            retriever,
            context_policy=knowledge_context_policy,
        )

        graph_builder.add_node(
            "retrieve_knowledge",
            cast(Any, retrieve_knowledge_node),
        )
        retrieval_node_name = "retrieve_knowledge"
        if personalized_tail is not None:
            graph_builder.add_edge(
                personalized_tail,
                "retrieve_knowledge",
            )

        graph_builder.add_edge(
            "retrieve_knowledge",
            "chat",
        )
    elif personalized_tail is not None:
        graph_builder.add_edge(
            personalized_tail,
            "chat",
        )

    personalized_target = personalized_entry or retrieval_node_name or "chat"
    general_target = retrieval_node_name or "chat"
    graph_builder.add_conditional_edges(
        "analyze_requirements",
        route_after_requirement_analysis,
        {
            "clarify": "clarify_requirements",
            "general": general_target,
            "personalized": personalized_target,
        },
    )

    # 提供工具时，创建工具执行节点和循环路由
    if tools:
        outfit_generation_node = create_outfit_generation_node(
            model,
            context_budget_policy=context_budget_policy,
        )
        outfit_correction_node = create_outfit_correction_node(
            model,
            context_budget_policy=context_budget_policy,
        )

        graph_builder.add_node(
            "tools",
            ToolNode(list(tools)),
        )
        graph_builder.add_node(
            "generate_outfit",
            cast(Any, outfit_generation_node),
        )
        graph_builder.add_node(
            "validate_outfit",
            cast(Any, validate_outfit),
        )
        graph_builder.add_node(
            "correct_outfit",
            cast(Any, outfit_correction_node),
        )
        graph_builder.add_node(
            "reject_tools",
            cast(Any, reject_disallowed_tool_calls),
        )

        # 根据模型回复判断执行工具还是结束
        graph_builder.add_conditional_edges(
            "chat",
            route_after_chat,
            {
                "tools": "tools",
                "reject_tools": "reject_tools",
                "generate_outfit": "generate_outfit",
                END: END,
            },
        )

        # 工具执行完成后回到聊天节点，让模型整理最终回答
        graph_builder.add_edge(
            "tools",
            "chat",
        )
        graph_builder.add_edge(
            "reject_tools",
            "chat",
        )
        graph_builder.add_edge(
            "generate_outfit",
            "validate_outfit",
        )
        graph_builder.add_conditional_edges(
            "validate_outfit",
            route_after_outfit_validation,
            {
                "correct_outfit": "correct_outfit",
                "end": END,
            },
        )
        graph_builder.add_edge(
            "correct_outfit",
            "validate_outfit",
        )
    else:
        # 没有提供工具时，聊天节点执行后直接结束
        graph_builder.add_edge(
            "chat",
            END,
        )

    # 编译后返回可以执行的工作流
    return graph_builder.compile(
        checkpointer=checkpointer,
    )
