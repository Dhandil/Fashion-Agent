"""穿搭方案仓库接口。"""

from typing import Protocol

from app.domain.entities.outfit import Outfit


class OutfitRepository(Protocol):
    """定义穿搭方案的持久化和查询能力。"""

    async def get_by_id(
        self,
        user_id: str,
        outfit_id: str,
    ) -> Outfit | None:
        """查询属于指定用户的一套穿搭方案。"""

        ...

    async def search(
        self,
        user_id: str,
        scenario: str | None = None,
        favorite_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Outfit]:
        """根据用户、场景和收藏状态查询穿搭。"""

        ...

    async def count(
        self,
        user_id: str,
        scenario: str | None = None,
        favorite_only: bool = False,
    ) -> int:
        """统计符合用户和过滤条件的穿搭数量。"""

        ...

    async def save(
        self,
        outfit: Outfit,
    ) -> Outfit:
        """新增或更新一套穿搭方案。"""

        ...

    async def delete(
        self,
        user_id: str,
        outfit_id: str,
    ) -> bool:
        """删除指定用户的一套穿搭方案。"""

        ...
