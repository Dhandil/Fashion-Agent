"""穿搭方案的内存仓库实现。"""

from collections.abc import Iterable

from app.domain.entities.outfit import Outfit


class InMemoryOutfitRepository:
    """在当前 Python 进程内保存穿搭方案。"""

    def __init__(
        self,
        outfits: Iterable[Outfit] | None = None,
    ) -> None:
        """使用可选的穿搭方案初始化仓库。"""

        # 用户 ID 和穿搭 ID 共同组成数据隔离键
        self._outfits = {
            (
                outfit.user_id,
                outfit.outfit_id,
            ): outfit
            for outfit in outfits or ()
        }

    async def get_by_id(
        self,
        user_id: str,
        outfit_id: str,
    ) -> Outfit | None:
        """查询属于指定用户的一套穿搭方案。"""

        return self._outfits.get(
            (
                user_id,
                outfit_id,
            ),
        )

    async def search(
        self,
        user_id: str,
        scenario: str | None = None,
        favorite_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Outfit]:
        """根据用户、场景和收藏状态查询穿搭。"""

        matched_outfits: list[Outfit] = []

        for outfit in self._outfits.values():
            # 不允许返回其他用户的穿搭方案
            if outfit.user_id != user_id:
                continue

            # 提供场景时执行精确过滤
            if (
                scenario is not None
                and outfit.scenario != scenario
            ):
                continue

            # 只查询收藏时，跳过未收藏方案
            if (
                favorite_only
                and not outfit.is_favorite
            ):
                continue

            matched_outfits.append(outfit)

        # 先过滤再切片，offset 表示跳过的匹配记录数
        return matched_outfits[
            offset : offset + limit
        ]

    async def count(
        self,
        user_id: str,
        scenario: str | None = None,
        favorite_only: bool = False,
    ) -> int:
        """统计符合用户和过滤条件的穿搭数量。"""

        matched_outfits = await self.search(
            user_id=user_id,
            scenario=scenario,
            favorite_only=favorite_only,
            limit=len(self._outfits),
            offset=0,
        )

        return len(matched_outfits)

    async def save(
        self,
        outfit: Outfit,
    ) -> Outfit:
        """新增或更新一套穿搭方案。"""

        outfit_key = (
            outfit.user_id,
            outfit.outfit_id,
        )
        self._outfits[outfit_key] = outfit

        return outfit

    async def delete(
        self,
        user_id: str,
        outfit_id: str,
    ) -> bool:
        """删除指定用户的一套穿搭方案。"""

        deleted_outfit = self._outfits.pop(
            (
                user_id,
                outfit_id,
            ),
            None,
        )

        return deleted_outfit is not None
