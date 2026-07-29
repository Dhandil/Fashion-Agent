from pydantic import BaseModel, Field


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
        description="用户发送给购物助手的消息",
    )


class ChatResponse(BaseModel):
    """聊天接口的响应模型。"""

    # 当前对话的会话 ID，客户端应在下一轮请求中继续传入
    conversation_id: str
    
    # Agent 返回给用户的文本回复
    message: str

    # RAG 回答引用的知识来源
    sources: list[str] = Field(
        default_factory=list,
        description="本次回答使用的知识文档来源",
    )