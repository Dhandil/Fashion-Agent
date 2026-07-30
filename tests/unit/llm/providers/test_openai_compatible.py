from unittest.mock import patch

import pytest

from app.core.config import Settings
from app.core.exceptions import ConfigurationError
from app.llm.providers.openai_compatible import create_chat_model


def test_create_chat_model_requires_api_key() -> None:
    """验证缺少 API Key 时抛出配置异常。"""

    # 显式提供模型名称，但不提供 API Key
    settings = Settings(
        _env_file=None,
        llm_api_key=None,
        llm_model="test-model",
    )

    # 验证异常类型和异常消息
    with pytest.raises(ConfigurationError, match="缺少 LLM_API_KEY 配置"):
        create_chat_model(settings)


def test_create_chat_model_requires_model_name() -> None:
    """验证缺少模型名称时抛出配置异常。"""

    # 提供测试密钥，但不提供模型名称
    settings = Settings(
        _env_file=None,
        llm_api_key="test_secret_key",
        llm_model=None,
    )

    # 验证异常类型和异常消息
    with pytest.raises(ConfigurationError, match="缺少 LLM_MODEL 配置"):
        create_chat_model(settings)


def test_ceate_chat_model_uses_settings() -> None:
    """验证 Provider 使用配置创建聊天模型。"""

    # 创建完整的测试配置
    settings = Settings(
        _env_file=None,
        llm_base_url="https://example.com/v1",
        llm_api_key="test-secret-key",
        llm_model="test-model",
    )

    # 临时替换 Provider 模块中的 ChatOpenAI
    with patch("app.llm.providers.openai_compatible.ChatOpenAI") as mocked_chat_openai:
        model = create_chat_model(settings)

    # 返回值应该是模拟 ChatOpenAI 创建出的对象
    assert model is mocked_chat_openai.return_value

    # 验证 ChatOpenAI 收到了正确配置
    mocked_chat_openai.assert_called_once_with(
        model="test-model",
        api_key=settings.llm_api_key,
        base_url="https://example.com/v1",
    )
