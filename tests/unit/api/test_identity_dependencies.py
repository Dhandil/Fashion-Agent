"""FastAPI 当前用户身份依赖测试。"""

import pytest
from fastapi import HTTPException

from app.api.dependencies.identity import (
    get_current_user,
)
from app.core.config import Settings


@pytest.mark.anyio
async def test_current_user_normalizes_development_header() -> None:
    """验证开发环境能够读取并清理用户 ID。"""

    settings = Settings(
        _env_file=None,
        app_env="development",
        debug=False,
    )

    current_user = await get_current_user(
        x_user_id="  user-001  ",
        settings=settings,
    )

    assert current_user.user_id == "user-001"


@pytest.mark.anyio
async def test_current_user_rejects_blank_user_id() -> None:
    """验证只包含空格的用户 ID 会被拒绝。"""

    settings = Settings(
        _env_file=None,
        app_env="test",
        debug=False,
    )

    with pytest.raises(HTTPException) as exception_info:
        await get_current_user(
            x_user_id="   ",
            settings=settings,
        )

    assert exception_info.value.status_code == 422
    assert exception_info.value.detail == ("X-User-ID 不能为空")


@pytest.mark.anyio
async def test_current_user_rejects_production_header() -> None:
    """验证生产环境禁止信任 X-User-ID 请求头。"""

    settings = Settings(
        _env_file=None,
        app_env="production",
        debug=False,
    )

    with pytest.raises(HTTPException) as exception_info:
        await get_current_user(
            x_user_id="user-001",
            settings=settings,
        )

    assert exception_info.value.status_code == 503
    assert "禁止在生产环境" in str(
        exception_info.value.detail,
    )
