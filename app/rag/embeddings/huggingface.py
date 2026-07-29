from langchain_huggingface import HuggingFaceEmbeddings

from app.core.config import Settings, get_settings


def create_huggingface_embeddings(
    settings: Settings | None = None,
) -> HuggingFaceEmbeddings:
    """根据项目配置创建本地 Hugging Face Embedding。"""

    # 测试可以传入独立配置，正常运行则读取全局配置
    current_settings = settings or get_settings()

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