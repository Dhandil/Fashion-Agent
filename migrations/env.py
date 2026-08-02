"""Alembic 异步数据库迁移环境。"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import get_settings
from app.core.exceptions import ConfigurationError
from app.db.models.base import Base
from app.db.models.outfit import (
    OutfitItemModel,
    OutfitModel,
)
from app.db.models.outfit_feedback import (
    OutfitFeedbackModel,
)
from app.db.models.preference_memory import (
    PreferenceMemoryModel,
)
from app.db.models.product import ProductModel
from app.db.models.style_profile import (
    StyleProfileModel,
)
from app.db.models.wardrobe_item import (
    WardrobeItemModel,
)

# Alembic 当前使用的配置对象
config = context.config

# 使用 alembic.ini 中定义的日志配置
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def configure_database_url() -> None:
    """将项目配置中的数据库地址写入 Alembic 配置。"""

    # 从 Fashion-Agent 的 Settings 和 .env 中读取数据库配置
    settings = get_settings()

    if settings.database_url is None:
        raise ConfigurationError(
            "未配置 DATABASE_URL，无法执行数据库迁移",
        )

    # 读取 SecretStr 中保存的真实连接地址
    database_url = settings.database_url.get_secret_value()

    # Alembic Config 使用百分号进行插值，因此需要转义 URL 中的百分号
    escaped_database_url = database_url.replace(
        "%",
        "%%",
    )

    # 运行时覆盖 alembic.ini 中的示例连接地址
    config.set_main_option(
        "sqlalchemy.url",
        escaped_database_url,
    )


# 显式引用全部模型，确保 Alembic 自动迁移能够发现所有数据表
_registered_models = (
    ProductModel,
    StyleProfileModel,
    WardrobeItemModel,
    OutfitModel,
    OutfitItemModel,
    OutfitFeedbackModel,
    PreferenceMemoryModel,
)

# 所有 SQLAlchemy 模型共享同一个 Base.metadata
target_metadata = Base.metadata

# 在执行迁移前加载项目数据库地址
configure_database_url()


def run_migrations_offline() -> None:
    """在不建立数据库连接的情况下生成迁移 SQL。"""

    database_url = config.get_main_option(
        "sqlalchemy.url",
    )

    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={
            "paramstyle": "named",
        },
        # 检测数据库字段类型变化
        compare_type=True,
        # 检测数据库服务器默认值变化
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(
    connection: Connection,
) -> None:
    """使用已经建立的同步连接上下文执行迁移。"""

    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """创建异步 Engine 并执行数据库迁移。"""

    # Alembic 迁移使用独立连接，不复用应用连接池
    connectable = async_engine_from_config(
        config.get_section(
            config.config_ini_section,
            {},
        ),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        # Alembic 内部迁移逻辑是同步接口，
        # run_sync 会在异步连接上安全执行它
        await connection.run_sync(
            do_run_migrations,
        )

    # 迁移完成后释放 Engine 资源
    await connectable.dispose()


def run_migrations_online() -> None:
    """在连接数据库的模式下运行异步迁移。"""

    asyncio.run(
        run_async_migrations(),
    )


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
