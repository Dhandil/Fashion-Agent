"""FastAPI 当前用户身份依赖。"""

from typing import Annotated

from fastapi import (
    Depends,
    Header,
    HTTPException,
    status,
)
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from app.core.config import (
    Settings,
    get_settings,
)


class CurrentUser(BaseModel):
    """经过身份依赖解析后的当前用户。"""

    user_id: str = Field(
        min_length=1,
        max_length=100,
    )

    model_config = ConfigDict(
        frozen=True,
    )


SettingsDependency = Annotated[
    Settings,
    Depends(get_settings),
]


async def get_current_user(
    x_user_id: Annotated[
        str,
        Header(
            alias="X-User-ID",
            min_length=1,
            max_length=100,
        ),
    ],
    settings: SettingsDependency,
) -> CurrentUser:
    """在开发环境中从请求头取得当前用户身份。"""

    # 生产环境不能信任客户端直接提供的用户 ID
    if settings.app_env not in {
        "development",
        "test",
    }:
        raise HTTPException(
            status_code=(status.HTTP_503_SERVICE_UNAVAILABLE),
            detail=("当前用户身份认证尚未配置，禁止在生产环境使用 X-User-ID"),
        )

    # 去除首尾空格，避免相同用户产生多个不同 ID
    normalized_user_id = x_user_id.strip()

    if not normalized_user_id:
        raise HTTPException(
            status_code=(status.HTTP_422_UNPROCESSABLE_CONTENT),
            detail="X-User-ID 不能为空",
        )

    return CurrentUser(
        user_id=normalized_user_id,
    )


CurrentUserDependency = Annotated[
    CurrentUser,
    Depends(get_current_user),
]
