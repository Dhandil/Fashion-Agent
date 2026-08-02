"""运行 Fashion-Agent 发布前质量门。"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

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
) -> tuple[QualityCheck, ...]:
    """根据是否启用 PostgreSQL 组合质量检查。"""

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
            environment={"DEBUG": "false"},
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
    failed_checks = tuple(
        check.name
        for check in build_quality_checks(
            include_postgres=args.postgres,
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
