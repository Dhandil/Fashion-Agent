"""用户穿搭档案仓库接口。"""

from typing import Protocol

from app.domain.entities.style_profile import StyleProfile


class StyleProfileRepository(Protocol):
    """定义用户穿搭档案的持久化能力。"""

    async def get_by_user_id(
        self,
        user_id: str,
    ) -> StyleProfile | None:
        """根据用户 ID 查询穿搭档案。"""

        ...

    async def save(
        self,
        profile: StyleProfile,
    ) -> StyleProfile:
        """新增或更新用户穿搭档案。"""

        ...

    async def delete_by_user_id(
        self,
        user_id: str,
    ) -> bool:
        """删除用户穿搭档案并返回是否成功。"""

        ...