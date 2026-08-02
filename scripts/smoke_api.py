"""对正在运行的 Fashion-Agent 执行只读 API 冒烟检查。"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from typing import Any

import httpx


class SmokeCheckError(RuntimeError):
    """API 可访问但响应结构不符合最小契约。"""


@dataclass(frozen=True, slots=True)
class SmokeCheck:
    """一条不会修改业务数据的 API 检查。"""

    name: str
    path: str
    required_keys: tuple[str, ...]
    authenticated: bool = True


READ_ONLY_CHECKS = (
    SmokeCheck(
        name="健康检查",
        path="/api/v1/health",
        required_keys=("status", "app_name", "environment"),
        authenticated=False,
    ),
    SmokeCheck(
        name="数据库就绪检查",
        path="/api/v1/health/ready",
        required_keys=("status", "checks"),
        authenticated=False,
    ),
    SmokeCheck(
        name="长期穿搭档案读取",
        path="/api/v1/style-profile",
        required_keys=("preferred_styles", "avoided_styles"),
    ),
    SmokeCheck(
        name="偏好记忆读取",
        path="/api/v1/style-profile/memories",
        required_keys=("items", "count", "include_expired"),
    ),
    SmokeCheck(
        name="衣橱列表读取",
        path="/api/v1/wardrobe?limit=1",
        required_keys=("items", "count", "total"),
    ),
    SmokeCheck(
        name="已保存 Outfit 列表读取",
        path="/api/v1/outfits?limit=1",
        required_keys=("items", "count", "total"),
    ),
)


def configure_utf8_output() -> None:
    """让 Windows 终端稳定显示中文检查结果。"""

    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8")


def validate_payload(
    check: SmokeCheck,
    payload: Any,
) -> None:
    """验证响应是对象并包含当前接口的最小稳定字段。"""

    if not isinstance(payload, dict):
        raise SmokeCheckError(
            f"{check.name} 响应不是 JSON 对象",
        )
    missing_keys = tuple(
        key
        for key in check.required_keys
        if key not in payload
    )
    if missing_keys:
        raise SmokeCheckError(
            f"{check.name} 缺少字段：{', '.join(missing_keys)}",
        )
    if check.path == "/api/v1/health" and payload["status"] != "ok":
        raise SmokeCheckError("健康检查状态不是 ok")
    if check.path == "/api/v1/health/ready" and (
        payload["status"] != "ready"
        or payload["checks"] != {"database": "ok"}
    ):
        raise SmokeCheckError("数据库就绪检查状态异常")


def run_smoke_checks(
    *,
    base_url: str,
    user_id: str,
    timeout: float,
    transport: httpx.BaseTransport | None = None,
) -> tuple[str, ...]:
    """执行全部只读检查并返回通过的检查名称。"""

    passed: list[str] = []
    with httpx.Client(
        base_url=base_url.rstrip("/"),
        timeout=timeout,
        transport=transport,
        # 本地服务检查不能被 VPN 或系统 HTTP 代理转发。
        trust_env=False,
    ) as client:
        for check in READ_ONLY_CHECKS:
            headers = (
                {"X-User-ID": user_id}
                if check.authenticated
                else None
            )
            response = client.get(
                check.path,
                headers=headers,
            )
            response.raise_for_status()
            validate_payload(check, response.json())
            print(f"[通过] {check.name}", flush=True)
            passed.append(check.name)
    return tuple(passed)


def parse_args() -> argparse.Namespace:
    """解析服务地址、测试身份和超时时间。"""

    parser = argparse.ArgumentParser(
        description="运行 Fashion-Agent 只读 API 冒烟检查。",
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="正在运行的 Fashion-Agent 根地址。",
    )
    parser.add_argument(
        "--user-id",
        default="fashion-agent-smoke-test",
        help="只用于读取空白用户空间的开发身份。",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="每个 HTTP 请求的超时秒数。",
    )
    return parser.parse_args()


def main() -> int:
    """运行冒烟检查并把失败转换为命令行退出码。"""

    configure_utf8_output()
    args = parse_args()
    try:
        passed = run_smoke_checks(
            base_url=args.base_url,
            user_id=args.user_id,
            timeout=args.timeout,
        )
    except (httpx.HTTPError, SmokeCheckError, ValueError) as exc:
        print(
            f"[失败] API 冒烟检查未通过：{type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 1

    print(f"全部 {len(passed)} 项只读 API 检查通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
