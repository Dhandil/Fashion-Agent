"""Pytest 全局测试配置。"""

import pytest


@pytest.fixture
def anyio_backend() -> str:
    """指定异步测试统一使用 Python asyncio 后端。"""

    return "asyncio"