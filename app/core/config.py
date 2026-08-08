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

    # OpenTelemetry 默认关闭；启用后才创建 SDK Provider 和 OTLP Exporter
    telemetry_enabled: bool = False

    # Trace 中使用的稳定服务名，不包含主机名或用户信息
    telemetry_service_name: str = Field(
        default="fashion-agent",
        min_length=1,
        max_length=100,
    )

    # OTLP gRPC Collector 地址，例如 http://otel-collector:4317
    telemetry_otlp_endpoint: str | None = None

    # 本地明文 Collector 可设为 True；生产环境默认要求 TLS
    telemetry_otlp_insecure: bool = False

    # ParentBased 概率采样，0 表示只传播父采样决定，1 表示记录全部根 Span
    telemetry_sample_ratio: float = Field(
        default=0.1,
        ge=0,
        le=1,
    )

    # PostgreSQL 异步连接地址
    # SecretStr 可以避免连接地址中的密码被日志直接打印
    database_url: SecretStr | None = None

    # 是否输出 SQLAlchemy 执行的 SQL，生产环境应保持关闭
    database_echo: bool = False

    # LangGraph 短期记忆后端：本地测试默认使用进程内存
    short_term_memory_backend: Literal[
        "memory",
        "redis",
    ] = "memory"

    # Redis Checkpointer 连接地址；使用 SecretStr 避免密码进入日志
    redis_url: SecretStr | None = None

    # Redis 会话在无活动后保留 7 天，读取会刷新过期时间
    redis_checkpoint_ttl_minutes: int = Field(
        default=10_080,
        ge=1,
        le=525_600,
    )

    # 每个会话、每个 Checkpoint 命名空间保留的最近快照数量
    # 最新快照本身包含完整当前状态，因此旧快照主要用于故障分析而不是恢复必需项
    redis_checkpoint_keep_last: int = Field(
        default=50,
        ge=1,
        le=1_000,
    )

    # OpenAI 兼容接口的基础地址
    llm_base_url: str | None = None

    # LLM 密钥，SecretStr 会在打印配置时隐藏真实内容
    llm_api_key: SecretStr | None = None

    # 使用的模型名称，例如 deepseek-chat
    llm_model: str | None = None

    # LLM 调用超时时间，避免模型响应慢时用户无限等待
    llm_timeout_seconds: float = Field(
        default=120.0,
        gt=0,
        le=600,
    )

    # LLM 调用最大重试次数（网络类临时错误）
    llm_max_retries: int = Field(
        default=2,
        ge=0,
        le=10,
    )

    # 衣物照片识别默认关闭；关闭时照片识别接口返回明确的 503
    wardrobe_vision_backend: Literal[
        "disabled",
        "openai_compatible",
    ] = "disabled"

    # OpenAI 兼容多模态接口地址，例如 https://vendor.example.com/v1
    wardrobe_vision_base_url: str | None = None

    # 视觉模型密钥，SecretStr 会在打印配置时隐藏真实内容
    wardrobe_vision_api_key: SecretStr | None = None

    # 支持图片输入的模型名称
    wardrobe_vision_model: str | None = None

    # 识别请求超时时间，避免用户长时间等待外部模型
    wardrobe_vision_timeout_seconds: float = Field(
        default=30.0,
        gt=0,
        le=120,
    )

    # 单张衣物照片允许的最大字节数，默认 5 MB
    wardrobe_image_max_bytes: int = Field(
        default=5 * 1024 * 1024,
        ge=1_024,
        le=20 * 1024 * 1024,
    )

    # 低于该置信度时，草稿中已识别的字段全部标记为需要用户确认
    wardrobe_draft_min_confidence: float = Field(
        default=0.5,
        ge=0,
        le=1,
    )

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

    # 模型已本地缓存时强制离线加载，跳过 HuggingFace 网络检查（国内网络尤其有用）
    embedding_hf_offline: bool = False

    # HuggingFace 镜像端点，例如 https://hf-mirror.com；需要下载模型时使用
    embedding_hf_endpoint: str | None = None

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

    # Retriever 返回后最多允许进入 Agent State 的知识片段数
    rag_context_max_documents: int = Field(
        default=3,
        ge=1,
        le=20,
    )

    # 单个检索片段进入 Agent State 前的最大字符数
    rag_context_max_fragment_chars: int = Field(
        default=1_200,
        ge=100,
        le=20_000,
    )

    # 全部检索片段进入 Agent State 前的总字符上限
    rag_context_max_chars: int = Field(
        default=4_000,
        ge=200,
        le=50_000,
    )

    # 单次模型调用允许注入的外部上下文字符预算
    # 当前用户消息和固定系统规则不计入此预算
    agent_context_max_chars: int = Field(
        default=12_000,
        ge=1_000,
        le=100_000,
    )

    # 用户明确维护的长期档案和上一套 Outfit 的分类预算
    agent_explicit_memory_max_chars: int = Field(
        default=3_000,
        ge=200,
        le=50_000,
    )

    # 对话摘要、近期 Outfit 和反馈等历史记忆的分类预算
    agent_historical_memory_max_chars: int = Field(
        default=3_000,
        ge=200,
        le=50_000,
    )

    # 单次模型调用允许使用的 RAG 知识分类预算
    agent_knowledge_max_chars: int = Field(
        default=4_000,
        ge=200,
        le=50_000,
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
