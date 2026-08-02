"""FastAPI 应用启动与关闭生命周期。"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.session import close_database_connections
from app.memory.short_term.checkpointer import (
    close_short_term_checkpointer,
    initialize_short_term_checkpointer,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def application_lifespan(
    _application: FastAPI,
) -> AsyncIterator[None]:
    """记录进程生命周期，并在退出时释放基础设施资源。"""

    await initialize_short_term_checkpointer()
    logger.info("Fashion-Agent application started")
    try:
        yield
    finally:
        try:
            await close_short_term_checkpointer()
        finally:
            await close_database_connections()
        logger.info("Fashion-Agent application stopped")
