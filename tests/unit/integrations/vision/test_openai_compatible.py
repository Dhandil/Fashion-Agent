"""OpenAI 兼容视觉识别 Provider 测试。"""

import json
from collections.abc import Callable

import httpx
import pytest

from app.core.exceptions import WardrobeVisionProviderError
from app.domain.entities.wardrobe_image import (
    WardrobeImage,
    WardrobeImageContentType,
)
from app.integrations.vision.openai_compatible import (
    OpenAICompatibleWardrobeImageRecognizer,
)

MockHandler = Callable[
    [httpx.Request],
    httpx.Response,
]

# 只需要合法的 JPEG 文件头，Provider 不解析图片内容
TEST_IMAGE = WardrobeImage(
    content=b"\xff\xd8\xff" + b"\x01" * 12,
    content_type=WardrobeImageContentType.JPEG,
)


def create_recognizer(
    handler: MockHandler,
) -> OpenAICompatibleWardrobeImageRecognizer:
    """创建使用 MockTransport 的适配器，保证测试不会访问网络。"""

    return OpenAICompatibleWardrobeImageRecognizer(
        base_url="https://vision.example.test/v1/",
        api_key="test-key",
        model="test-vision-model",
        timeout_seconds=5,
        client=httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
        ),
    )


def create_completion_response(
    recognition: dict[str, object],
) -> httpx.Response:
    """构造 Chat Completions 风格的成功响应。"""

    return httpx.Response(
        200,
        json={
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            recognition,
                            ensure_ascii=False,
                        ),
                    },
                },
            ],
        },
    )


@pytest.mark.anyio
async def test_recognizer_sends_image_and_parses_result() -> None:
    """验证请求包含照片与提示，并解析结构化识别结果。"""

    requests: list[httpx.Request] = []

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        requests.append(request)
        return create_completion_response(
            {
                "name": "浅蓝色亚麻衬衫",
                "category": "衬衫",
                "colors": [
                    "浅蓝色",
                ],
                "materials": [
                    "亚麻",
                ],
                "uncertain_fields": [
                    "materials",
                ],
                "confidence": 0.82,
            },
        )

    recognizer = create_recognizer(handler)

    recognition = await recognizer.recognize(
        TEST_IMAGE,
        "这是一件夏季衬衫",
    )

    assert recognition.name == "浅蓝色亚麻衬衫"
    assert recognition.category == "衬衫"
    assert recognition.confidence == 0.82
    assert recognition.uncertain_fields == (
        "materials",
    )

    assert len(requests) == 1
    request = requests[0]
    assert str(request.url) == ("https://vision.example.test/v1/chat/completions")
    assert request.headers["Authorization"] == "Bearer test-key"

    payload = json.loads(
        request.content.decode("utf-8"),
    )
    assert payload["model"] == "test-vision-model"
    # 部分 OpenAI 兼容视觉模型不支持 response_format，JSON 约束完全交给系统提示词
    assert "response_format" not in payload

    user_content = payload["messages"][1]["content"]
    assert "这是一件夏季衬衫" in user_content[0]["text"]
    assert user_content[1]["image_url"]["url"].startswith(
        "data:image/jpeg;base64,",
    )


@pytest.mark.anyio
async def test_recognizer_ignores_identity_fields_from_model() -> None:
    """验证模型伪造的用户和衣橱单品 ID 不会进入识别结果。"""

    def handler(
        _request: httpx.Request,
    ) -> httpx.Response:
        return create_completion_response(
            {
                "name": "白色运动鞋",
                "category": "鞋履",
                "confidence": 0.7,
                "user_id": "user-999",
                "wardrobe_item_id": "wardrobe-999",
            },
        )

    recognizer = create_recognizer(handler)

    recognition = await recognizer.recognize(
        TEST_IMAGE,
    )

    assert not hasattr(
        recognition,
        "user_id",
    )
    assert not hasattr(
        recognition,
        "wardrobe_item_id",
    )


@pytest.mark.anyio
async def test_recognizer_reports_http_failure() -> None:
    """验证外部服务错误转换为明确的识别失败。"""

    def handler(
        _request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(500)

    recognizer = create_recognizer(handler)

    with pytest.raises(WardrobeVisionProviderError):
        await recognizer.recognize(
            TEST_IMAGE,
        )


@pytest.mark.anyio
async def test_recognizer_reports_timeout() -> None:
    """验证请求超时不会把异常直接抛给上层业务。"""

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        raise httpx.ReadTimeout(
            "timeout",
            request=request,
        )

    recognizer = create_recognizer(handler)

    with pytest.raises(WardrobeVisionProviderError):
        await recognizer.recognize(
            TEST_IMAGE,
        )


@pytest.mark.anyio
@pytest.mark.parametrize(
    "body",
    [
        {},
        {
            "choices": [],
        },
        {
            "choices": [
                {
                    "message": {
                        "content": "",
                    },
                },
            ],
        },
        {
            "choices": [
                {
                    "message": {
                        "content": "不是 JSON",
                    },
                },
            ],
        },
        {
            "choices": [
                {
                    "message": {
                        "content": "[1, 2]",
                    },
                },
            ],
        },
    ],
)
async def test_recognizer_rejects_invalid_response(
    body: dict[str, object],
) -> None:
    """验证缺少结果、空结果和非法 JSON 都被拒绝。"""

    def handler(
        _request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            200,
            json=body,
        )

    recognizer = create_recognizer(handler)

    with pytest.raises(WardrobeVisionProviderError):
        await recognizer.recognize(
            TEST_IMAGE,
        )


@pytest.mark.anyio
async def test_recognizer_rejects_invalid_confidence() -> None:
    """验证不符合约定结构的识别结果不会进入领域对象。"""

    def handler(
        _request: httpx.Request,
    ) -> httpx.Response:
        return create_completion_response(
            {
                "name": "黑色大衣",
                "category": "外套",
                "confidence": 3.5,
            },
        )

    recognizer = create_recognizer(handler)

    with pytest.raises(WardrobeVisionProviderError):
        await recognizer.recognize(
            TEST_IMAGE,
        )
