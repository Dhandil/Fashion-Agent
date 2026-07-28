from langchain_openai import ChatOpenAI

from app.core.config import Settings, get_settings
from app.core.exceptions import ConfigurationError


def create_chat_model(settings: Settings | None) -> ChatOpenAI:
    """根据项目配置创建 OpenAI 兼容发聊天模型。"""

    # 如果调用者没有传入配置，则读取项目全局配置
    current_settings = settings or get_settings()

    # API Key 是调用模型的必要配置
    if current_settings.llm_api_key is None:
        raise ConfigurationError("缺少 LLM_API_KEY 配置")

    # 模型名称也是必要配置
    if current_settings.llm_model is None:
        raise ConfigurationError("缺少 LLM_MODEL 配置")

    # 创建 LangChain 聊天模型，但此时不会立即发送网络请求
    return ChatOpenAI(
        model=current_settings.llm_model,
        api_key=current_settings.llm_api_key.get_secret_value(),
        base_url=current_settings.llm_base_url,
    )