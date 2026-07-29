from unittest.mock import patch

from app.core.config import Settings
from app.rag.embeddings.huggingface import create_huggingface_embeddings


def test_create_huggingface_embeddings_uses_settings() -> None:
    """验证 Embedding Provider 正确使用项目配置。"""

    # 创建测试配置，不读取本地 .env
    settings = Settings(
        _env_file=None,
        embedding_model="test-embedding-model",
        embedding_device="cpu",
    )

    # 替换真实 HuggingFaceEmbeddings，避免下载模型
    with patch(
        "app.rag.embeddings.huggingface.HuggingFaceEmbeddings",
    ) as mocked_embeddings:
        embeddings = create_huggingface_embeddings(settings)

    # Provider 应返回适配器创建的对象
    assert embeddings is mocked_embeddings.return_value

    # 验证模型参数正确传入
    mocked_embeddings.assert_called_once_with(
        model_name="test-embedding-model",
        model_kwargs={
            "device": "cpu",
        },
        encode_kwargs={
            "normalize_embeddings": True,
        },
    )