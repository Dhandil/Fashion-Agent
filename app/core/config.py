from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
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

    # 商品仓库实现类型：当前默认使用内存仓库
    product_repository_backend: Literal[
        "memory",
        "postgres",
    ] = "memory"

    # PostgreSQL 异步连接地址
    # SecretStr 可以避免连接地址中的密码被日志直接打印
    database_url: SecretStr | None = None

    # 是否输出 SQLAlchemy 执行的 SQL，生产环境应保持关闭
    database_echo: bool = False

    # OpenAI 兼容接口的基础地址
    llm_base_url: str | None = None

    # LLM 密钥，SecretStr 会在打印配置时隐藏真实内容
    llm_api_key: SecretStr | None = None

    # 使用的模型名称，例如 deepseek-chat
    llm_model: str | None = None

    # 天气 Provider 默认关闭；启用后 Agent 才会注册天气查询工具
    weather_provider_backend: Literal[
        "disabled",
        "open_meteo",
    ] = "disabled"

    # Open-Meteo 地点搜索和预报服务地址，允许生产环境切换客户或自托管端点
    weather_geocoding_base_url: str = "https://geocoding-api.open-meteo.com"
    weather_forecast_base_url: str = "https://api.open-meteo.com"

    # 商业客户端点需要 API Key；本地非商业原型可以留空
    weather_api_key: SecretStr | None = None

    # 外部天气请求超时时间，避免请求长期占用 Agent 执行链路
    weather_timeout_seconds: float = Field(
        default=10.0,
        gt=0,
        le=60,
    )

    # 配置 Pydantic Settings 读取项目根目录下的.env文件
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        # 环境变量名称不区分大小写
        case_sensitive=False,
        # 忽略 .env 中暂时没有再 Settings 中声明的配置
        extra="ignore",
    )

    # 本地 Embedding 模型名称
    embedding_model: str = "BAAI/bge-small-zh-v1.5"

    # Embedding 运行设备，开发环境默认使用 CPU
    embedding_device: str = "cpu"

    # Chroma 持久化数据保存目录
    chroma_persist_directory: str = "./data/chroma"

    # Chroma 中保存服装知识的集合名称
    chroma_collection_name: str = "fashion_knowledge"

    # 独立知识库根目录；其中的原文件只读，不由应用修改
    knowledge_repository_path: str = "./data/raw/Fashion-Agent-Knowledge"

    # 相对知识库根目录的正式发布 Manifest
    knowledge_release_manifest: str = "releases/manifests/fashion-knowledge-2.8.0.yaml"

    # 每个知识片段允许的最大字符数
    rag_chunk_size: int = 400

    # 相邻知识片段之间保留的重叠字符数
    rag_chunk_overlap: int = 50

    # 每次语义检索返回的知识片段数量
    rag_top_k: int = 3

    # 向量初筛候选数量，随后根据知识标题和标签执行本地重排
    rag_candidate_k: int = 24

    # 单次模型调用允许注入的外部上下文字符预算
    # 当前用户消息和固定系统规则不计入此预算
    agent_context_max_chars: int = Field(
        default=12_000,
        ge=1_000,
        le=100_000,
    )

    # 聊天模型最多接收的最近完整对话轮数；当前轮始终保留
    agent_history_max_turns: int = Field(
        default=6,
        ge=1,
        le=50,
    )

    # 聊天模型历史消息的字符预算；当前工具调用链不会被截断
    agent_history_max_chars: int = Field(
        default=8_000,
        ge=1_000,
        le=100_000,
    )

    # 提取式滚动摘要的字符预算，不额外调用模型
    agent_summary_max_chars: int = Field(
        default=2_000,
        ge=200,
        le=20_000,
    )


@lru_cache
def get_settings() -> Settings:
    """
    获取全局配置实例。

    lru_cache 会缓存Settings对象，避免程序每次使用配置时都
    重新读取一次 .env 文件。
    """

    return Settings()
