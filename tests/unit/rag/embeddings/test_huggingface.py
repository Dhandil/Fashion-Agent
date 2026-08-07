import os
from unittest.mock import patch

import pytest

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


@pytest.mark.parametrize(
    ("offline", "endpoint"),
    [
        (True, None),
        (False, "https://hf-mirror.com"),
        (True, "https://hf-mirror.com"),
    ],
)
def test_create_huggingface_embeddings_sets_hf_env(
    offline: bool,
    endpoint: str | None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """验证离线与镜像配置会写入 HuggingFace 环境变量。"""

    # 清理可能残留的环境变量，保证断言可预测
    monkeypatch.delenv("HF_HUB_OFFLINE", raising=False)
    monkeypatch.delenv("HF_ENDPOINT", raising=False)

    settings = Settings(
        _env_file=None,
        embedding_model="test-embedding-model",
        embedding_device="cpu",
        embedding_hf_offline=offline,
        embedding_hf_endpoint=endpoint,
    )

    with patch(
        "app.rag.embeddings.huggingface.HuggingFaceEmbeddings",
    ):
        create_huggingface_embeddings(settings)

    expected_offline = "1" if offline else None
    assert os.environ.get("HF_HUB_OFFLINE") == expected_offline
    assert os.environ.get("HF_ENDPOINT") == endpoint


def test_create_huggingface_embeddings_defaults_leave_env_untouched(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """验证默认配置（未开启离线/镜像）不污染进程环境变量。"""

    monkeypatch.delenv("HF_HUB_OFFLINE", raising=False)
    monkeypatch.delenv("HF_ENDPOINT", raising=False)

    settings = Settings(
        _env_file=None,
        embedding_model="test-embedding-model",
        embedding_device="cpu",
    )

    with patch(
        "app.rag.embeddings.huggingface.HuggingFaceEmbeddings",
    ):
        create_huggingface_embeddings(settings)

    assert os.environ.get("HF_HUB_OFFLINE") is None
    assert os.environ.get("HF_ENDPOINT") is None