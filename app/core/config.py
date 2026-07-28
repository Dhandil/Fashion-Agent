from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """项目全局配置

    配置值优先从系统环境变量读取；
    如果环境变量不存在，则使用这里定义的默认值。
    """

    # 应用基础配置
    app_name: str = "Fashion-Agent"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = False

    # 日志输出级别
    log_level: str = "INFO"

    # OpenAI 兼容接口的基础地址
    llm_base_url: str | None = None

    # LLM 密钥，SecretStr 会在打印配置时隐藏真实内容
    llm_api_key: SecretStr | None = None

    # 使用的模型名称，例如 deepseek-chat
    llm_model: str | None = None

    # 配置 Pydantic Settings 读取项目根目录下的.env文件
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        # 环境变量名称不区分大小写
        case_sensitive=False,
        # 忽略 .env 中暂时没有再 Settings 中声明的配置
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """
    获取全局配置实例。

    lru_cache 会缓存Settings对象，避免程序每次使用配置时都
    重新读取一次 .env 文件。
    """

    return Settings()
