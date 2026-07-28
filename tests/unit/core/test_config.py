from app.core.config import Settings


def test_settings_use_default_values() -> None:
    """验证没有读取.env时，配置使用代码中的默认值"""

    # _env_file=None 表示本次测试不去读取项目根目录下的c.env
    settings = Settings(_env_file=None)

    # 验证配置对象中的默认值是否符合预期
    assert settings.app_name == "Fashion-Agent"
    assert settings.app_env == "development"
    assert settings.app_host == "0.0.0.0"
    assert settings.app_port == 8000
    assert settings.debug is False
    assert settings.log_level == "INFO"


def test_settings_read_environment_variables(monkeypatch) -> None:
    """验证系统环境变量可以覆盖代码中的默认配置。"""

    # 临时设置环境变量，只在当前测试期间生效
    monkeypatch.setenv("APP_PORT", "9000")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    # 不读取 .env，只验证上面设置的系统环境变量
    settings = Settings(_env_file=None)

    # Pydantic 应该完成字符串到目标类型的自动转换
    assert settings.app_port == 9000
    assert settings.debug is True
    assert settings.log_level == "DEBUG"

def test_llm_api_key_is_masked(monkeypatch) -> None:
    """验证 LLM API Key 使用敏感字符串保存。"""

    # 临时设置测试密钥，不使用任何真实 API Key
    monkeypatch.setenv("LLM_API_KEY", "test-secret-key")

    # 不读取本地 .env， 保证测试只使用上面的临时变量
    settings = Settings(_env_file=None)

    # 确认配置中已经读取到密钥对象
    assert settings.llm_api_key is not None

    #只有明确调用 get_secret_value() 才能取得原始密钥
    assert settings.llm_api_key.get_secret_value() == "test-secret-key"

    # 直接转成字符串时，真实密钥不应该出现
    assert "test-secret-key" not in str(settings.llm_api_key)