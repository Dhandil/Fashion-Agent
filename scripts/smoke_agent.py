"""对真实 RAG 与付费聊天模型执行一次显式授权的冒烟检查。"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from typing import Any

import httpx

DEFAULT_MESSAGE = (
    "请根据知识库简短说明：夏天通勤选择亚麻有什么优点和注意事项？"
    "不要查询或推荐商品。"
)


class AgentSmokeError(RuntimeError):
    """真实 Agent 响应不满足最小产品契约。"""


@dataclass(frozen=True, slots=True)
class AgentSmokeResult:
    """一次真实 Agent 冒烟调用的安全摘要。"""

    conversation_id: str
    message_length: int
    sources: tuple[str, ...]


def configure_utf8_output() -> None:
    """让 Windows 终端稳定显示中文检查结果。"""

    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8")


def validate_agent_payload(payload: Any) -> AgentSmokeResult:
    """校验真实回答、会话标识和 RAG 来源。"""

    if not isinstance(payload, dict):
        raise AgentSmokeError("Agent 响应不是 JSON 对象")

    conversation_id = payload.get("conversation_id")
    message = payload.get("message")
    sources = payload.get("sources")
    if not isinstance(conversation_id, str) or not conversation_id:
        raise AgentSmokeError("Agent 响应缺少 conversation_id")
    if not isinstance(message, str) or not message.strip():
        raise AgentSmokeError("Agent 没有返回文本回答")
    if (
        not isinstance(sources, list)
        or not sources
        or not all(
            isinstance(source, str) and source
            for source in sources
        )
    ):
        raise AgentSmokeError("Agent 没有返回有效的 RAG 来源")

    return AgentSmokeResult(
        conversation_id=conversation_id,
        message_length=len(message),
        sources=tuple(sources),
    )


def run_agent_smoke(
    *,
    base_url: str,
    user_id: str,
    message: str,
    timeout: float,
    transport: httpx.BaseTransport | None = None,
) -> AgentSmokeResult:
    """调用一次真实聊天接口并验证 RAG 来源。"""

    with httpx.Client(
        base_url=base_url.rstrip("/"),
        timeout=timeout,
        transport=transport,
        # 本地容器请求不能被 VPN 或系统代理转发。
        trust_env=False,
    ) as client:
        response = client.post(
            "/api/v1/chat",
            headers={"X-User-ID": user_id},
            json={"message": message},
        )
        response.raise_for_status()
        return validate_agent_payload(response.json())


def parse_args() -> argparse.Namespace:
    """解析显式授权开关和服务参数。"""

    parser = argparse.ArgumentParser(
        description="运行一次会下载 Embedding 并调用付费模型的 Agent 冒烟检查。",
    )
    parser.add_argument(
        "--allow-model-call",
        action="store_true",
        help="明确允许本次真实模型调用；未提供时脚本拒绝执行。",
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
    )
    parser.add_argument(
        "--user-id",
        default="fashion-agent-model-smoke-test",
    )
    parser.add_argument(
        "--message",
        default=DEFAULT_MESSAGE,
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=300.0,
    )
    return parser.parse_args()


def main() -> int:
    """只有显式授权时才调用真实模型。"""

    configure_utf8_output()
    args = parse_args()
    if not args.allow_model_call:
        print(
            "[拒绝] 该检查会调用真实模型，请显式提供 --allow-model-call。",
            file=sys.stderr,
        )
        return 2

    try:
        result = run_agent_smoke(
            base_url=args.base_url,
            user_id=args.user_id,
            message=args.message,
            timeout=args.timeout,
        )
    except (httpx.HTTPError, AgentSmokeError, ValueError) as exc:
        print(
            f"[失败] Agent 冒烟检查未通过：{type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 1

    print(
        f"[通过] Agent 返回 {result.message_length} 个字符，"
        f"命中 {len(result.sources)} 个知识来源。",
    )
    for source in result.sources:
        print(f"- {source}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
