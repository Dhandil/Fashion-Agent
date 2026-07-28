from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """聊天接口的请求模型。"""

    # 用户输入的消息，长度限制为 1 到 2000 个字符
    message: str = Field(
        min_length=1,
        max_length=2000,
        description="用户发送给购物助手的消息",
    )


class ChatResponse(BaseModel):
    """聊天接口的响应模型。"""

    # Agent 返回给用户的文本回复
    message: str