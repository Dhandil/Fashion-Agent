from typing import Annotated, NotRequired, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

from app.agents.schemas.requirements import (
    OutfitRequirementAnalysis,
)
from app.agents.schemas.style_profile import (
    StyleProfileSnapshot,
)
from app.domain.entities.outfit import (
    OutfitRecommendation,
)
from app.domain.entities.outfit_gap import (
    OutfitGapReport,
)
from app.domain.entities.outfit_validation import (
    OutfitFeasibilityReport,
)
from app.domain.entities.weather import WeatherContext
from app.memory.short_term.conversation_summary import (
    ConversationSummary,
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

    # 当前请求明确提供的天气，只对本轮穿搭决策有效
    weather_context: NotRequired[WeatherContext | None]

    # 用户已确认的历史 Outfit 反馈形成的个性化参考
    outfit_feedback_context: NotRequired[str]

    # 用户近期保存的 Outfit，用于减少连续重复相同衣物组合
    recent_outfits_context: NotRequired[str]

    # 已退出最近消息窗口的人机文本提取式摘要，只用于理解连续意图
    conversation_summary: NotRequired[ConversationSummary | None]

    # 用户明确维护的长期穿搭档案
    style_profile_context: NotRequired[str]

    # 不含用户 ID 的结构化长期档案，用于确定性偏好合并
    style_profile_snapshot: NotRequired[StyleProfileSnapshot | None]

    # Agent 生成的结构化穿搭推荐；普通问答时可以不存在
    outfit_recommendation: NotRequired[OutfitRecommendation | None]

    # 无法形成可执行 Outfit 时返回的结构化缺口
    outfit_gap_report: NotRequired[OutfitGapReport | None]

    # 结构化推荐经过确定性规则检查后的结果
    outfit_feasibility_report: NotRequired[OutfitFeasibilityReport | None]

    # 当前轮可执行性失败后的修正次数，硬限制为最多一次
    outfit_correction_attempts: NotRequired[int]

    # 最近一次成功生成的 Outfit，作为后续局部调整的结构化基线
    previous_outfit_recommendation: NotRequired[OutfitRecommendation | None]

    # 当前轮结构化需求分析，用于数据加载和工具权限的确定性路由
    requirement_analysis: NotRequired[OutfitRequirementAnalysis]

    # 防止模型在同一轮反复请求被策略拒绝的工具
    tool_policy_rejection_count: NotRequired[int]
