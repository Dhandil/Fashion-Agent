from pydantic import BaseModel, Field

from app.api.schemas.weather import WeatherContextInput
from app.domain.entities.outfit import (
    OutfitRecommendation,
)
from app.domain.entities.outfit_gap import OutfitGapReport
from app.domain.entities.outfit_validation import (
    OutfitFeasibilityIssue,
)


class ChatRequest(BaseModel):
    """聊天接口的请求模型。"""

    conversation_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="用于保存多轮对话状态的会话 ID",
    )

    # 用户输入的消息，长度限制为 1 到 2000 个字符
    message: str = Field(
        min_length=1,
        max_length=2000,
        description="用户发送给个人穿搭助手的消息",
    )

    # 可由前端定位和天气服务明确提供；不提供时 Agent 不虚构实时天气
    weather: WeatherContextInput | None = None


class ChatResponse(BaseModel):
    """聊天接口的响应模型。"""

    # 当前对话的会话 ID，客户端应在下一轮请求中继续传入
    conversation_id: str

    # Agent 返回给用户的文本回复
    message: str

    # 只有生成完整穿搭时才返回结构化 Outfit
    outfit: OutfitRecommendation | None = Field(
        default=None,
        description="本次生成的结构化穿搭推荐",
    )

    # 当前真实候选不足以生成完整 Outfit 时返回
    outfit_gap: OutfitGapReport | None = Field(
        default=None,
        description="无法形成完整穿搭时的结构化缺口",
    )

    # RAG 回答引用的知识来源
    sources: list[str] = Field(
        default_factory=list,
        description="本次回答使用的知识文档来源",
    )

    # 结构化 Outfit 的确定性错误或风险提示
    outfit_issues: list[OutfitFeasibilityIssue] = Field(
        default_factory=list,
        description="本次穿搭可执行性检查发现的问题",
    )
