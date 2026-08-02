import pytest
from pydantic import ValidationError

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
    assert settings.weather_provider_backend == "disabled"
    assert settings.weather_timeout_seconds == 10.0
    assert settings.knowledge_repository_path == ("./data/raw/Fashion-Agent-Knowledge")
    assert settings.knowledge_release_manifest == (
        "releases/manifests/fashion-knowledge-2.8.0.yaml"
    )
    assert settings.rag_candidate_k == 24
    assert settings.agent_context_max_chars == 12_000
    assert settings.agent_history_max_turns == 6
    assert settings.agent_history_max_chars == 8_000
    assert settings.agent_summary_max_chars == 2_000


def test_settings_reject_invalid_context_budget(
    monkeypatch,
) -> None:
    """验证上下文预算不能小于保障基本事实所需的下限。"""

    monkeypatch.setenv(
        "AGENT_CONTEXT_MAX_CHARS",
        "999",
    )

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


@pytest.mark.parametrize(
    ("variable_name", "value"),
    (
        ("AGENT_HISTORY_MAX_TURNS", "0"),
        ("AGENT_HISTORY_MAX_CHARS", "999"),
        ("AGENT_SUMMARY_MAX_CHARS", "199"),
    ),
)
def test_settings_reject_invalid_history_window(
    monkeypatch,
    variable_name: str,
    value: str,
) -> None:
    """验证历史消息轮数和字符预算不能低于安全下限。"""

    monkeypatch.setenv(variable_name, value)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


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

    # 只有明确调用 get_secret_value() 才能取得原始密钥
    assert settings.llm_api_key.get_secret_value() == "test-secret-key"

    # 直接转成字符串时，真实密钥不应该出现
    assert "test-secret-key" not in str(settings.llm_api_key)


def test_settings_read_database_environment_variables(
    monkeypatch,
) -> None:
    """验证数据库配置能够从环境变量读取并转换类型。"""

    # 模拟生产环境提供的数据库配置
    monkeypatch.setenv(
        "PRODUCT_REPOSITORY_BACKEND",
        "postgres",
    )
    monkeypatch.setenv(
        "DATABASE_URL",
        ("postgresql+asyncpg://fashion_agent:secret@localhost:5432/fashion_agent"),
    )
    monkeypatch.setenv(
        "DATABASE_ECHO",
        "true",
    )

    # 不读取项目的 .env，只验证测试设置的环境变量
    settings = Settings(_env_file=None)

    # 仓库后端应该切换为 PostgreSQL
    assert settings.product_repository_backend == "postgres"

    # SecretStr 需要显式调用方法才能取得真实内容
    assert settings.database_url is not None
    assert settings.database_url.get_secret_value() == (
        "postgresql+asyncpg://fashion_agent:secret@localhost:5432/fashion_agent"
    )

    # Pydantic 应将字符串 true 转换为布尔值
    assert settings.database_echo is True


def test_settings_reject_invalid_repository_backend(
    monkeypatch,
) -> None:
    """验证不支持的商品仓库类型会触发配置校验错误。"""

    # 设置一个不在 Literal 允许范围内的仓库类型
    monkeypatch.setenv(
        "PRODUCT_REPOSITORY_BACKEND",
        "mongodb",
    )

    # Settings 初始化时应该立即拒绝无效配置
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_settings_read_weather_environment_variables(
    monkeypatch,
) -> None:
    """验证天气 Provider、端点、密钥和超时可以通过环境变量配置。"""

    monkeypatch.setenv(
        "WEATHER_PROVIDER_BACKEND",
        "open_meteo",
    )
    monkeypatch.setenv(
        "WEATHER_GEOCODING_BASE_URL",
        "https://customer-geocoding-api.open-meteo.com",
    )
    monkeypatch.setenv(
        "WEATHER_FORECAST_BASE_URL",
        "https://customer-api.open-meteo.com",
    )
    monkeypatch.setenv(
        "WEATHER_API_KEY",
        "test-weather-key",
    )
    monkeypatch.setenv(
        "WEATHER_TIMEOUT_SECONDS",
        "15",
    )

    settings = Settings(_env_file=None)

    assert settings.weather_provider_backend == "open_meteo"
    assert settings.weather_geocoding_base_url == ("https://customer-geocoding-api.open-meteo.com")
    assert settings.weather_forecast_base_url == ("https://customer-api.open-meteo.com")
    assert settings.weather_api_key is not None
    assert settings.weather_api_key.get_secret_value() == "test-weather-key"
    assert settings.weather_timeout_seconds == 15.0


@pytest.mark.parametrize(
    "timeout",
    (
        "0",
        "61",
    ),
)
def test_settings_reject_invalid_weather_timeout(
    monkeypatch,
    timeout: str,
) -> None:
    """验证天气超时必须大于零且不超过六十秒。"""

    monkeypatch.setenv(
        "WEATHER_TIMEOUT_SECONDS",
        timeout,
    )

    with pytest.raises(ValidationError):
        Settings(_env_file=None)
