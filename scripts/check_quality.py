"""运行 Fashion-Agent 发布前质量门。"""

from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Docker Compose 默认映射的宿主端口（见 deployments/docker/compose.yaml）
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

# 目录占位文件可以提交，真实运行数据和本地配置不能进入 Git。
PROTECTED_EXACT_PATHS = frozenset({".env"})
PROTECTED_PREFIXES = (
    ".venv/",
    "data/raw/",
    "data/chroma/",
)
PROTECTED_PLACEHOLDERS = frozenset(
    {
        "data/raw/.gitkeep",
        "data/chroma/.gitkeep",
    },
)


@dataclass(frozen=True, slots=True)
class QualityCheck:
    """一条可以按顺序执行的本地质量检查。"""

    name: str
    command: tuple[str, ...]
    environment: dict[str, str] = field(
        default_factory=dict,
    )


def normalize_git_path(path: str) -> str:
    """把 Git 路径统一为仓库相对的正斜杠格式。"""

    normalized = path.replace("\\", "/")
    if normalized.startswith("./"):
        return normalized[2:]
    return normalized


def is_protected_tracked_path(path: str) -> bool:
    """判断一个已跟踪路径是否属于禁止提交的本地数据。"""

    normalized = normalize_git_path(path)
    if normalized in PROTECTED_PLACEHOLDERS:
        return False
    if normalized in PROTECTED_EXACT_PATHS:
        return True
    return normalized.startswith(PROTECTED_PREFIXES)


def find_protected_tracked_paths(
    tracked_paths: tuple[str, ...],
) -> tuple[str, ...]:
    """稳定排序返回所有不应被 Git 跟踪的路径。"""

    return tuple(
        sorted(
            path
            for path in tracked_paths
            if is_protected_tracked_path(path)
        ),
    )


def configure_utf8_output() -> None:
    """在 Windows 终端中统一脚本及子进程的中文输出编码。"""

    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8")


def read_tracked_paths() -> tuple[str, ...]:
    """从 Git 读取已经进入索引的全部路径。"""

    result = subprocess.run(
        ("git", "ls-files", "-z"),
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
    )
    return tuple(
        path
        for path in result.stdout.decode("utf-8").split("\0")
        if path
    )


def build_quality_checks(
    *,
    include_postgres: bool,
    include_redis: bool = False,
    include_rag_evaluation: bool = False,
    include_outfit_evaluation: bool = False,
) -> tuple[QualityCheck, ...]:
    """根据是否启用真实基础设施组合质量检查。"""

    python = sys.executable
    checks: list[QualityCheck] = [
        QualityCheck(
            name="Git 空白错误检查",
            command=("git", "diff", "--check"),
        ),
        QualityCheck(
            name="Ruff 代码规范检查",
            command=(
                python,
                "-m",
                "ruff",
                "check",
                "app",
                "tests",
                "scripts",
                "migrations",
            ),
        ),
        QualityCheck(
            name="mypy 静态类型检查",
            command=(python, "-m", "mypy", "app"),
        ),
        QualityCheck(
            name="默认自动化测试",
            command=(python, "-m", "pytest", "tests", "-q"),
            # 本地受保护 .env 不参与质量门的测试配置。
            # 默认测试使用禁用天气的确定性配置；真实天气联调单独执行。
            environment={
                "DEBUG": "false",
                "WEATHER_PROVIDER_BACKEND": "disabled",
            },
        ),
    ]

    if include_postgres:
        checks.extend(
            (
                QualityCheck(
                    name="Alembic 模型一致性检查",
                    command=(python, "-m", "alembic", "check"),
                    environment={"DEBUG": "false"},
                ),
                QualityCheck(
                    name="PostgreSQL 真实仓库测试",
                    command=(
                        python,
                        "-m",
                        "pytest",
                        "tests/integration/db",
                        "-q",
                    ),
                    environment={
                        "DEBUG": "false",
                        "RUN_POSTGRES_TESTS": "true",
                    },
                ),
            ),
        )

    if include_redis:
        checks.append(
            QualityCheck(
                name="Redis Checkpointer 持久化测试",
                command=(
                    python,
                    "-m",
                    "pytest",
                    "tests/integration/memory",
                    "-q",
                ),
                environment={
                    "DEBUG": "false",
                    "RUN_REDIS_TESTS": "true",
                    "REDIS_URL": os.getenv(
                        "REDIS_URL",
                        "redis://localhost:6379/0",
                    ),
                },
            ),
        )

    if include_rag_evaluation:
        checks.append(
            QualityCheck(
                name="知识检索质量评估",
                command=(
                    python,
                    "-m",
                    "scripts.evaluate_knowledge_retrieval",
                    "--no-write",
                ),
                # 测试和评测都不能被本地 .env 中的非法 DEBUG 值污染。
                # 模型已本地缓存时跳过 HuggingFace 网络检查。
                environment={
                    "DEBUG": "false",
                    "HF_HUB_OFFLINE": "1",
                },
            ),
        )

    if include_outfit_evaluation:
        checks.append(
            QualityCheck(
                name="Outfit 生成与修正评测",
                command=(
                    python,
                    "-m",
                    "scripts.evaluate_outfits",
                ),
                environment={"DEBUG": "false"},
            ),
        )

    return tuple(checks)


def run_check(check: QualityCheck) -> bool:
    """执行一条检查并打印便于定位失败步骤的标题。"""

    print(f"\n==> {check.name}", flush=True)
    environment = os.environ.copy()
    environment.update(check.environment)
    environment["PYTHONUTF8"] = "1"
    environment["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(
        check.command,
        cwd=PROJECT_ROOT,
        env=environment,
        check=False,
    )
    if result.returncode == 0:
        print(f"[通过] {check.name}", flush=True)
        return True
    print(
        f"[失败] {check.name}，退出码 {result.returncode}",
        flush=True,
    )
    return False


def probe_tcp_port(host: str, port: int, timeout: float = 1.0) -> bool:
    """TCP 探测一个端口是否可连接，用于判断基础设施服务是否就绪。"""

    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def detect_infrastructure_services(
    *,
    host: str = "127.0.0.1",
) -> tuple[bool, bool]:
    """探测 PostgreSQL 与 Redis 是否已在本机运行。

    返回 (postgres_ready, redis_ready)。仅做 TCP 探测，
    不验证凭据——服务端口开放即可纳入真实集成测试。
    """

    return (
        probe_tcp_port(host, POSTGRES_PORT),
        probe_tcp_port(host, REDIS_PORT),
    )


def rag_evaluation_ready() -> bool:
    """判断知识检索评估是否可运行：问题集存在且 Chroma 索引非空。"""

    cases_path = Path("evaluation/rag/retrieval_cases.json")
    chroma_dir = Path("data/chroma")
    return cases_path.exists() and chroma_dir.exists()


def parse_args() -> argparse.Namespace:
    """解析质量门命令行参数。"""

    parser = argparse.ArgumentParser(
        description="运行 Fashion-Agent 发布前质量检查。",
    )
    parser.add_argument(
        "--postgres",
        action="store_true",
        help="同时检查 Alembic 并运行真实 PostgreSQL 集成测试。",
    )
    parser.add_argument(
        "--redis",
        action="store_true",
        help="同时运行真实 Redis Checkpointer 持久化测试。",
    )
    parser.add_argument(
        "--no-auto-detect",
        action="store_true",
        help="关闭基础设施自动探测（默认自动纳入已就绪的 PostgreSQL/Redis 集成测试）。",
    )
    parser.add_argument(
        "--rag-evaluation",
        action="store_true",
        help="运行知识检索质量评估（通过率低于 100% 时该检查失败）。",
    )
    parser.add_argument(
        "--outfit-evaluation",
        action="store_true",
        help="运行 Outfit 生成与修正评测（调用真实 LLM，较慢；有失败案例时该检查失败）。",
    )
    return parser.parse_args()


def main() -> int:
    """先检查敏感路径，再依次运行全部质量检查。"""

    configure_utf8_output()
    args = parse_args()
    protected_paths = find_protected_tracked_paths(
        read_tracked_paths(),
    )
    if protected_paths:
        print("[失败] 以下本地配置或运行数据已被 Git 跟踪：")
        for path in protected_paths:
            print(f"- {path}")
        print("请先将它们移出 Git 索引，再运行质量门。")
        return 1

    print("[通过] 未发现被 Git 跟踪的受保护本地数据。")

    # 自动探测已就绪的基础设施；显式传参或 --no-auto-detect 时跳过探测
    postgres_ready, redis_ready = (
        (False, False)
        if args.no_auto_detect
        else detect_infrastructure_services()
    )
    include_postgres = args.postgres or postgres_ready
    include_redis = args.redis or redis_ready

    # 知识检索评估：显式传参或检测到问题集 + Chroma 索引时纳入
    rag_ready = rag_evaluation_ready()
    include_rag_evaluation = args.rag_evaluation or (
        rag_ready and not args.no_auto_detect
    )

    if args.no_auto_detect:
        print("[提示] 已关闭基础设施自动探测。")
    else:
        if postgres_ready:
            print("[检测] PostgreSQL 端口就绪，纳入真实集成测试。")
        else:
            print(
                "[提示] 未检测到 PostgreSQL（127.0.0.1:5432），跳过 4 个数据库集成测试；"
                "可运行 `docker compose up -d postgres` 后重试。",
            )
        if redis_ready:
            print("[检测] Redis 端口就绪，纳入真实集成测试。")
        else:
            print(
                "[提示] 未检测到 Redis（127.0.0.1:6379），跳过 3 个 Checkpointer 集成测试；"
                "可运行 `docker compose up -d redis` 后重试。",
            )
        if include_rag_evaluation:
            print("[检测] 检测到知识库索引与问题集，纳入知识检索质量评估。")
        else:
            print(
                "[提示] 未检测到知识库索引或问题集，跳过知识检索质量评估；"
                "可运行 `python -m scripts.index_knowledge` 与 `python -m scripts.evaluate_knowledge_retrieval` 后重试。",
            )

    failed_checks = tuple(
        check.name
        for check in build_quality_checks(
            include_postgres=include_postgres,
            include_redis=include_redis,
            include_rag_evaluation=include_rag_evaluation,
            include_outfit_evaluation=args.outfit_evaluation,
        )
        if not run_check(check)
    )
    if failed_checks:
        print("\n质量门未通过：")
        for name in failed_checks:
            print(f"- {name}")
        return 1

    print("\n全部质量检查通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
