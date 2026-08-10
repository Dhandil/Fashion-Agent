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

严格输出一个 JSON 对象，不要 Markdown 代码块，不要任何解释性文字。JSON 字段：
- name：字符串，简洁衣物名称，例如“浅蓝色亚麻衬衫”
- category：字符串，具体品类，例如“衬衫”“长裤”“鞋履”“外套”
- colors：字符串数组，主要颜色
- materials：字符串数组，可辨认面料，看不出就留空
- style_tags：字符串数组，风格标签
- seasons：字符串数组，适用季节
- scenarios：字符串数组，适用场景
- uncertain_fields：字符串数组，上述字段中不确定、需要用户确认的字段名
- confidence：0 到 1 之间的数字，表示整体识别置信度
- notes：字符串，需要用户注意的补充说明，可为空

必须遵守：
1. 只描述照片中确实能看到的特征，看不出来的字段留空。
2. 不猜测品牌、尺码、价格、购买渠道和衣物是否干净可用。
3. 面料只有在纹理明显可辨时才给出，否则留空并写入 uncertain_fields。
4. 不描述人物、面部、体型和背景环境。
5. 全部文本使用简体中文。"""

_DEFAULT_USER_PROMPT = "请识别这张照片中的衣物。"
_MULTI_SYSTEM_PROMPT = _SYSTEM_PROMPT.replace(
    "严格输出一个 JSON 对象",
    "严格输出一个 JSON 数组；数组中的每个元素都是一个衣物 JSON 对象",
) + "\n6. 如果照片中有多件衣物，每件衣物分别输出一个元素；只能确认一件时数组只包含一个元素。"


def _extract_json_value(content: str) -> object:
    """从模型输出中提取 JSON 对象或数组。

    优先直接解析；同时兼容常见的模型输出形态：
    - Markdown 代码块包裹（```json ... ```）
    - JSON 前后夹带解释性文字
    """

    text = content.strip()
    try:
        return json.loads(text)
    except ValueError:
        pass

    # 提取 ```json ... ``` 或 ``` ... ``` 代码块
    if "```" in text:
        for block in text.split("```"):
            candidate = block.strip()
            if candidate.startswith("json"):
                candidate = candidate[4:].strip()
            if candidate.startswith(("{", "[")):
                try:
                    return json.loads(candidate)
                except ValueError:
                    continue

    # 提取第一个对象或数组到对应结尾之间的内容
    starts = [index for index in (text.find("{"), text.find("[")) if index != -1]
    if starts:
        first = min(starts)
        end_char = "}" if text[first] == "{" else "]"
        last = text.rfind(end_char)
        if last > first:
            try:
                return json.loads(text[first : last + 1])
            except ValueError:
                pass

    raise ValueError("模型输出中未找到 JSON 对象或数组")


def _extract_json_object(content: str) -> object:
    """从模型输出中提取 JSON 对象，并拒绝数组。"""

    value = _extract_json_value(content)
    if isinstance(value, Mapping):
        return value
    raise ValueError("模型输出不是 JSON 对象")


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

    async def recognize_many(
        self,
        image: WardrobeImage,
        hint: str | None = None,
    ) -> tuple[WardrobeItemRecognition, ...]:
        """识别同一张照片中的一件或多件衣物。"""

        payload = self._build_payload(image=image, hint=hint, multiple=True)
        if self._client is not None:
            return await self._recognize_many_with_client(
                client=self._client,
                payload=payload,
            )

        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            return await self._recognize_many_with_client(
                client=client,
                payload=payload,
            )

    def _build_payload(
        self,
        *,
        image: WardrobeImage,
        hint: str | None,
        multiple: bool = False,
    ) -> dict[str, object]:
        """构造多模态请求体，照片以 Data URI 随请求发送。"""

        encoded_image = b64encode(
            image.content,
        ).decode("ascii")
        data_uri = f"data:{image.content_type.value};base64,{encoded_image}"

        normalized_hint = hint.strip() if hint is not None else ""
        user_prompt = (
            "请识别这张照片中的一件或多件衣物，并按要求返回 JSON 数组。"
            if multiple
            else _DEFAULT_USER_PROMPT
        )
        user_text = (
            f"{user_prompt}用户补充说明：{normalized_hint}"
            if normalized_hint
            else user_prompt
        )

        return {
            "model": self._model,
            # 识别属于事实描述任务，使用确定性输出
            "temperature": 0,
            # 不强制 response_format：部分 OpenAI 兼容视觉模型只支持纯文本模型
            # 使用该参数，JSON 结构改为完全依赖系统提示词约束，并由解析阶段兜底拒绝非法结果
            "messages": [
                {
                    "role": "system",
                    "content": _MULTI_SYSTEM_PROMPT if multiple else _SYSTEM_PROMPT,
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

        body = await self._request_body(client=client, payload=payload)
        return self._parse_recognition(body)

    async def _recognize_many_with_client(
        self,
        *,
        client: httpx.AsyncClient,
        payload: Mapping[str, object],
    ) -> tuple[WardrobeItemRecognition, ...]:
        """请求并解析一张照片中的多件衣物。"""

        body = await self._request_body(client=client, payload=payload)
        return self._parse_recognitions(body)

    async def _request_body(
        self,
        *,
        client: httpx.AsyncClient,
        payload: Mapping[str, object],
    ) -> object:
        """发送请求并统一转换网络错误。"""

        try:
            response = await client.post(
                f"{self._base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json=payload,
                timeout=self._timeout_seconds,
            )
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise WardrobeVisionProviderError(
                "衣物照片识别服务暂时不可用，请稍后重试或手动录入。",
            ) from exc

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
            recognition_payload: object = _extract_json_object(
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

    @staticmethod
    def _parse_recognitions(
        body: object,
    ) -> tuple[WardrobeItemRecognition, ...]:
        """解析多结果响应；兼容模型误返回单个对象的情况。"""

        if not isinstance(body, Mapping):
            raise WardrobeVisionProviderError("衣物照片识别服务返回了无效数据。")
        choices = body.get("choices")
        if not isinstance(choices, list) or not choices:
            raise WardrobeVisionProviderError("衣物照片识别服务没有返回识别结果。")
        first_choice = choices[0]
        message = first_choice.get("message") if isinstance(first_choice, Mapping) else None
        content = message.get("content") if isinstance(message, Mapping) else None
        if not isinstance(content, str) or not content.strip():
            raise WardrobeVisionProviderError("衣物照片识别服务返回了空结果。")

        try:
            payload = _extract_json_value(content)
            values = [payload] if isinstance(payload, Mapping) else payload
            if not isinstance(values, list) or not values:
                raise ValueError("结果数组为空")
            recognitions = tuple(
                WardrobeItemRecognition.model_validate(value)
                for value in values
                if isinstance(value, Mapping)
            )
            if not recognitions or len(recognitions) != len(values):
                raise ValueError("结果数组包含无效元素")
            return recognitions
        except (TypeError, ValueError) as exc:
            raise WardrobeVisionProviderError(
                "衣物照片识别结果不符合约定结构。",
            ) from exc
