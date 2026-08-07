import os

from langchain_huggingface import HuggingFaceEmbeddings

from app.core.config import Settings, get_settings


def create_huggingface_embeddings(
    settings: Settings | None = None,
) -> HuggingFaceEmbeddings:
    """根据项目配置创建本地 Hugging Face Embedding。"""

    # 测试可以传入独立配置，正常运行则读取全局配置
    current_settings = settings or get_settings()

    # 模型已缓存时可强制离线加载，跳过 HuggingFace 网络检查；
    # 需要下载模型时可通过镜像端点加速。两者均为进程级默认值。
    if current_settings.embedding_hf_offline:
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
    if current_settings.embedding_hf_endpoint:
        os.environ.setdefault("HF_ENDPOINT", current_settings.embedding_hf_endpoint)

    # 创建本地 Embedding 模型对象
    return HuggingFaceEmbeddings(
        model_name=current_settings.embedding_model,
        model_kwargs={
            "device": current_settings.embedding_device,
        },
        encode_kwargs={
            "normalize_embeddings": True,
        },
    )
