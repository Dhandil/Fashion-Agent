"""对衣物照片识别接口执行一次显式授权的真实冒烟检查。

脚本只把图片短暂编码后提交给识别接口，不会写入项目目录或保存图片。
默认拒绝真实模型调用，必须显式传入 ``--allow-model-call``。
"""

from __future__ import annotations

import argparse
import base64
import mimetypes
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx


class VisionSmokeError(RuntimeError):
    """识别接口返回不符合最小契约。"""


@dataclass(frozen=True, slots=True)
class VisionSmokeResult:
    """一次视觉识别冒烟调用的摘要，不包含图片或模型原始响应。"""

    draft_id: str
    confidence: float
    missing_fields: tuple[str, ...]
    uncertain_fields: tuple[str, ...]


def configure_utf8_output() -> None:
    """让 Windows 终端稳定输出中文。"""

    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8")


def detect_content_type(image_path: Path) -> str:
    """根据扩展名转换为 API 接受的图片类型。"""

    content_type, _ = mimetypes.guess_type(image_path.name)
    if content_type not in {"image/jpeg", "image/png"}:
        raise VisionSmokeError("图片必须是 JPEG 或 PNG 文件。")
    return content_type


def validate_draft_payload(payload: Any) -> VisionSmokeResult:
    """只检查草稿的公开字段，不打印照片内容或模型原始文本。"""

    if not isinstance(payload, dict):
        raise VisionSmokeError("识别响应不是 JSON 对象。")

    draft_id = payload.get("draft_id")
    confidence = payload.get("confidence")
    missing_fields = payload.get("missing_fields")
    uncertain_fields = payload.get("uncertain_fields")
    if not isinstance(draft_id, str) or not draft_id:
        raise VisionSmokeError("识别草稿缺少 draft_id。")
    if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
        raise VisionSmokeError("识别草稿 confidence 不在 0 到 1 范围内。")
    if not isinstance(missing_fields, list) or not all(
        isinstance(item, str) for item in missing_fields
    ):
        raise VisionSmokeError("识别草稿 missing_fields 格式无效。")
    if not isinstance(uncertain_fields, list) or not all(
        isinstance(item, str) for item in uncertain_fields
    ):
        raise VisionSmokeError("识别草稿 uncertain_fields 格式无效。")

    return VisionSmokeResult(
        draft_id=draft_id,
        confidence=float(confidence),
        missing_fields=tuple(missing_fields),
        uncertain_fields=tuple(uncertain_fields),
    )


def run_vision_smoke(
    *,
    image_path: Path,
    base_url: str,
    user_id: str,
    timeout: float,
    transport: httpx.BaseTransport | None = None,
) -> VisionSmokeResult:
    """向本地 App 发起一次照片识别请求并验证草稿契约。"""

    if not image_path.is_file():
        raise VisionSmokeError(f"找不到图片文件：{image_path}")
    content_type = detect_content_type(image_path)
    encoded_image = base64.b64encode(image_path.read_bytes()).decode("ascii")

    with httpx.Client(
        base_url=base_url.rstrip("/"),
        timeout=timeout,
        transport=transport,
        trust_env=False,
    ) as client:
        response = client.post(
            "/api/v1/wardrobe/recognitions",
            headers={"X-User-ID": user_id},
            json={
                "image_base64": encoded_image,
                "content_type": content_type,
            },
        )
        response.raise_for_status()
        return validate_draft_payload(response.json())


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""

    parser = argparse.ArgumentParser(
        description="执行一次显式授权的真实衣物照片识别冒烟检查。",
    )
    parser.add_argument("image", type=Path, help="待识别的 JPEG 或 PNG 图片路径")
    parser.add_argument(
        "--allow-model-call",
        action="store_true",
        help="明确允许本次调用外部视觉模型",
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--user-id", default="fashion-agent-vision-smoke-test")
    parser.add_argument("--timeout", type=float, default=120.0)
    return parser.parse_args()


def main() -> int:
    """执行冒烟检查并输出不含图片内容的摘要。"""

    configure_utf8_output()
    args = parse_args()
    if not args.allow_model_call:
        print(
            "[拒绝] 该检查会调用真实视觉模型，请显式提供 --allow-model-call。",
            file=sys.stderr,
        )
        return 2

    try:
        result = run_vision_smoke(
            image_path=args.image,
            base_url=args.base_url,
            user_id=args.user_id,
            timeout=args.timeout,
        )
    except (httpx.HTTPError, OSError, VisionSmokeError, ValueError) as exc:
        print(
            f"[失败] 视觉识别冒烟检查未通过：{type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 1

    print(
        f"[通过] 草稿 {result.draft_id}，置信度 {result.confidence:.2f}，"
        f"缺失字段 {len(result.missing_fields)} 个，"
        f"待确认字段 {len(result.uncertain_fields)} 个。",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
