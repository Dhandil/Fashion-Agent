"""发布前质量门测试。"""

from scripts.check_quality import (
    build_quality_checks,
    configure_utf8_output,
    find_protected_tracked_paths,
    is_protected_tracked_path,
    normalize_git_path,
)


def test_normalize_git_path_supports_windows_separator() -> None:
    """验证 Windows 路径会转换成 Git 风格。"""

    assert normalize_git_path(r"data\raw\secret.md") == (
        "data/raw/secret.md"
    )


def test_protected_path_check_allows_placeholders() -> None:
    """验证目录占位文件可提交，真实本地数据不可提交。"""

    assert is_protected_tracked_path("data/raw/.gitkeep") is False
    assert is_protected_tracked_path("data/chroma/.gitkeep") is False
    assert is_protected_tracked_path(".env.example") is False
    assert is_protected_tracked_path(".env") is True
    assert is_protected_tracked_path("data/raw/knowledge.md") is True
    assert is_protected_tracked_path("data/chroma/chroma.sqlite3") is True
    assert is_protected_tracked_path(".venv/Scripts/python.exe") is True


def test_find_protected_paths_is_stable_and_filtered() -> None:
    """验证违规路径结果经过过滤并稳定排序。"""

    assert find_protected_tracked_paths(
        (
            "data/raw/.gitkeep",
            "data/chroma/store.bin",
            "app/main.py",
            ".env",
        ),
    ) == (
        ".env",
        "data/chroma/store.bin",
    )


def test_postgres_checks_are_explicitly_opt_in() -> None:
    """验证默认质量门不依赖 Docker，开启参数后才检查数据库。"""

    default_names = {
        check.name
        for check in build_quality_checks(
            include_postgres=False,
            include_redis=False,
        )
    }
    postgres_names = {
        check.name
        for check in build_quality_checks(
            include_postgres=True,
            include_redis=False,
        )
    }

    assert "Alembic 模型一致性检查" not in default_names
    assert "PostgreSQL 真实仓库测试" not in default_names
    assert "Alembic 模型一致性检查" in postgres_names
    assert "PostgreSQL 真实仓库测试" in postgres_names


def test_redis_checks_are_explicitly_opt_in() -> None:
    """验证只有显式参数才连接 Redis 运行真实持久化测试。"""

    default_names = {
        check.name
        for check in build_quality_checks(
            include_postgres=False,
            include_redis=False,
        )
    }
    redis_names = {
        check.name
        for check in build_quality_checks(
            include_postgres=False,
            include_redis=True,
        )
    }

    assert "Redis Checkpointer 持久化测试" not in default_names
    assert "Redis Checkpointer 持久化测试" in redis_names


def test_rag_evaluation_is_read_only_and_isolated_from_local_env() -> None:
    """验证 RAG 质量评估不会覆盖基线，也不会读取非法本地 DEBUG。"""

    checks = build_quality_checks(
        include_postgres=False,
        include_redis=False,
        include_rag_evaluation=True,
    )
    rag_check = next(
        check
        for check in checks
        if check.name == "知识检索质量评估"
    )

    assert "--no-write" in rag_check.command
    assert rag_check.environment["DEBUG"] == "false"


def test_outfit_evaluation_isolated_from_local_env() -> None:
    """验证 Outfit 评测同样不受本地 .env 的 DEBUG 值污染。"""

    checks = build_quality_checks(
        include_postgres=False,
        include_redis=False,
        include_outfit_evaluation=True,
    )
    outfit_check = next(
        check
        for check in checks
        if check.name == "Outfit 生成与修正评测"
    )

    assert outfit_check.environment["DEBUG"] == "false"


def test_configure_utf8_output_is_safe_under_pytest() -> None:
    """验证捕获输出流不支持 reconfigure 时也不会失败。"""

    configure_utf8_output()
