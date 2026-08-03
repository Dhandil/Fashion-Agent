"""OpenAI 兼容视觉模型的衣物照片识别 Provider。"""

import json
from base64 import b64encode
from collections.abc import Mapping

import httpx

from app.core.exceptions import WardrobeVisionProviderError
from app.domain.entities.wardrobe_draft import (
    WardrobeItemRecognition,
)
from app.domain.entities.wardrobe_image import WardrobeImage

# 识别规则强调如实描述照片，宁可留空也不猜测无法看到的信息
_SYSTEM_PROMPT = """你是服装识别助手，只负责描述照片中这一件衣物的客观特征。

必须遵守：
1. 只描述照片中确实能看到的特征，看不出来的字段留空。
2. 不猜测品牌、尺码、价格、购买渠道和衣物是否干净可用。
3. 面料只有在纹理明显可辨时才给出，否则留空并写入 uncertain_fields。
4. 不描述人物、面部、体型和背景环境。
5. 只输出 JSON 对象，不输出解释性文字。

JSON 字段：
- name：字符串，简洁的衣物名称，例如“浅蓝色亚麻衬衫”。
- category：字符串，衣物品类，例如“衬衫”“长裤”“鞋履”。
- colors：字符串数组，主要颜色。
- materials：字符串数组，可辨认的面料。
- style_tags：字符串数组，风格标签。
- seasons：字符串数组，适用季节。
- scenarios：字符串数组，适用场景。
- uncertain_fields：字符串数组，上述字段中不确定、需要用户确认的字段名。
- confidence：0 到 1 之间的数字，表示整体识别置信度。
- notes：字符串，需要用户注意的补充说明，可为空。

全部文本使用简体中文。"""

_DEFAULT_USER_PROMPT = "请识别这张照片中的衣物。"


class OpenAICompatibleWardrobeImageRecognizer:
    """通过 OpenAI 兼容的多模态 Chat Completions 接口识别衣物照片。"""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float = 30.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        """保存连接参数；传入 client 便于测试时使用 MockTransport。"""

        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._client = client

    async def recognize(
        self,
        image: WardrobeImage,
        hint: str | None = None,
    ) -> WardrobeItemRecognition:
        """把照片和识别规则发送给视觉模型，并解析结构化结果。"""

        payload = self._build_payload(
            image=image,
            hint=hint,
        )

        if self._client is not None:
            return await self._recognize_with_client(
                client=self._client,
                payload=payload,
            )

        # 默认每次调用使用独立客户端，避免 Provider 缓存后遗漏关闭连接
        async with httpx.AsyncClient(
            timeout=self._timeout_seconds,
        ) as client:
            return await self._recognize_with_client(
                client=client,
                payload=payload,
            )

    def _build_payload(
        self,
        *,
        image: WardrobeImage,
        hint: str | None,
    ) -> dict[str, object]:
        """构造多模态请求体，照片以 Data URI 随请求发送。"""

        encoded_image = b64encode(
            image.content,
        ).decode("ascii")
        data_uri = f"data:{image.content_type.value};base64,{encoded_image}"

        normalized_hint = hint.strip() if hint is not None else ""
        user_text = (
            f"{_DEFAULT_USER_PROMPT}用户补充说明：{normalized_hint}"
            if normalized_hint
            else _DEFAULT_USER_PROMPT
        )

        return {
            "model": self._model,
            # 识别属于事实描述任务，使用确定性输出
            "temperature": 0,
            "response_format": {
                "type": "json_object",
            },
            "messages": [
                {
                    "role": "system",
                    "content": _SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": user_text,
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": data_uri,
                            },
                        },
                    ],
                },
            ],
        }

    async def _recognize_with_client(
        self,
        *,
        client: httpx.AsyncClient,
        payload: Mapping[str, object],
    ) -> WardrobeItemRecognition:
        """统一处理网络、HTTP 状态码和响应结构错误。"""

        try:
            response = await client.post(
                f"{self._base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                },
                json=payload,
                timeout=self._timeout_seconds,
            )
            response.raise_for_status()
            body: object = response.json()
        except (
            httpx.HTTPError,
            ValueError,
        ) as exc:
            # 错误信息不包含请求体、照片和模型原文
            raise WardrobeVisionProviderError(
                "衣物照片识别服务暂时不可用，请稍后重试或手动录入。",
            ) from exc

        return self._parse_recognition(
            body,
        )

    @staticmethod
    def _parse_recognition(
        body: object,
    ) -> WardrobeItemRecognition:
        """从 Chat Completions 响应中解析结构化识别结果。"""

        if not isinstance(body, Mapping):
            raise WardrobeVisionProviderError(
                "衣物照片识别服务返回了无效数据。",
            )

        choices = body.get("choices")
        if not isinstance(choices, list) or not choices:
            raise WardrobeVisionProviderError(
                "衣物照片识别服务没有返回识别结果。",
            )

        first_choice = choices[0]
        if not isinstance(first_choice, Mapping):
            raise WardrobeVisionProviderError(
                "衣物照片识别服务返回了无效数据。",
            )

        message = first_choice.get("message")
        if not isinstance(message, Mapping):
            raise WardrobeVisionProviderError(
                "衣物照片识别服务返回了无效数据。",
            )

        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise WardrobeVisionProviderError(
                "衣物照片识别服务返回了空结果。",
            )

        try:
            recognition_payload: object = json.loads(
                content,
            )
        except ValueError as exc:
            raise WardrobeVisionProviderError(
                "衣物照片识别结果不是有效 JSON。",
            ) from exc

        if not isinstance(recognition_payload, Mapping):
            raise WardrobeVisionProviderError(
                "衣物照片识别结果不是 JSON 对象。",
            )

        try:
            # 领域实体会忽略模型多输出的字段，例如伪造的用户或单品 ID
            return WardrobeItemRecognition.model_validate(
                recognition_payload,
            )
        except ValueError as exc:
            raise WardrobeVisionProviderError(
                "衣物照片识别结果不符合约定结构。",
            ) from exc
