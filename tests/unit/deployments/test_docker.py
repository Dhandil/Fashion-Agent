"""Docker 部署配置测试。"""

from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[3]
COMPOSE_PATH = (
    PROJECT_ROOT / "deployments" / "docker" / "compose.yaml"
)
DOCKERFILE_PATH = (
    PROJECT_ROOT / "deployments" / "docker" / "Dockerfile"
)


def load_compose() -> dict[str, object]:
    """读取并解析可提交的 Compose 配置。"""

    return yaml.safe_load(
        COMPOSE_PATH.read_text(encoding="utf-8"),
    )


def test_compose_separates_migration_and_app() -> None:
    """验证迁移成功后才启动 API，并等待 PostgreSQL 健康。"""

    compose = load_compose()
    services = compose["services"]
    assert isinstance(services, dict)
    migrate = services["migrate"]
    app = services["app"]
    assert migrate["command"] == ["alembic", "upgrade", "head"]
    assert app["depends_on"]["migrate"]["condition"] == (
        "service_completed_successfully"
    )
    assert app["depends_on"]["postgres"]["condition"] == (
        "service_healthy"
    )
    assert app["depends_on"]["redis"]["condition"] == (
        "service_healthy"
    )


def test_compose_preserves_data_boundaries() -> None:
    """验证知识只读挂载，Chroma 和模型缓存独立保存。"""

    compose = load_compose()
    services = compose["services"]
    assert isinstance(services, dict)
    app = services["app"]
    volumes = app["volumes"]
    assert any(
        volume.endswith(
            "/app/data/raw/Fashion-Agent-Knowledge:ro",
        )
        for volume in volumes
    )
    assert any(
        volume.endswith("/app/data/chroma")
        for volume in volumes
    )
    assert app["environment"]["DATABASE_URL"].find(
        "@postgres:5432/",
    ) > 0


def test_compose_uses_database_readiness() -> None:
    """验证容器健康检查使用真实数据库 readiness。"""

    compose = load_compose()
    services = compose["services"]
    assert isinstance(services, dict)
    health_command = " ".join(
        services["app"]["healthcheck"]["test"],
    )
    assert "/api/v1/health/ready" in health_command


def test_compose_provides_persistent_redis_8() -> None:
    """验证短期记忆使用具备必要模块的持久化 Redis 8。"""

    compose = load_compose()
    services = compose["services"]
    volumes = compose["volumes"]
    assert isinstance(services, dict)
    assert isinstance(volumes, dict)

    redis = services["redis"]
    app = services["app"]
    assert redis["image"].startswith("redis:8")
    assert "fashion_agent_redis_data:/data" in redis["volumes"]
    assert "fashion_agent_redis_data" in volumes
    assert app["environment"]["SHORT_TERM_MEMORY_BACKEND"] == "redis"
    assert app["environment"]["REDIS_URL"] == "redis://redis:6379/0"


def test_dockerfile_runs_as_non_root_python_311() -> None:
    """验证运行镜像版本、用户和复制边界。"""

    dockerfile = DOCKERFILE_PATH.read_text(
        encoding="utf-8",
    )
    assert "FROM python:3.11-slim-bookworm" in dockerfile
    assert "USER fashion_agent" in dockerfile
    assert "download.pytorch.org/whl/cpu" in dockerfile
    assert "PIP_DEFAULT_TIMEOUT=600" in dockerfile
    assert "PIP_RETRIES=10" in dockerfile
    assert "PIP_NO_CACHE_DIR=0" in dockerfile
    assert "--mount=type=cache,target=/root/.cache/pip" in dockerfile
    assert "python -m pip install . --no-deps" in dockerfile
    assert "COPY ." not in dockerfile
    assert "EXPOSE 8000" in dockerfile

    # 大体积 PyTorch 层必须位于项目文件 COPY 之前，避免代码变化重复下载
    assert dockerfile.index("torch>=2.2,<3.0") < dockerfile.index(
        "COPY pyproject.toml README.md ./"
    )
    assert dockerfile.index("COPY pyproject.toml README.md ./") < (
        dockerfile.index("COPY app ./app")
    )


def test_dockerignore_excludes_secrets_and_runtime_data() -> None:
    """验证构建上下文不会包含密钥、知识原文和 Chroma 数据。"""

    dockerignore = (
        PROJECT_ROOT / ".dockerignore"
    ).read_text(encoding="utf-8")
    ignored_lines = {
        line.strip()
        for line in dockerignore.splitlines()
        if line.strip() and not line.startswith("#")
    }
    assert ".env" in ignored_lines
    assert ".venv" in ignored_lines
    assert "data/raw" in ignored_lines
    assert "data/chroma" in ignored_lines
