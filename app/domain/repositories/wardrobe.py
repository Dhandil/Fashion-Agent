"""用户衣橱仓库接口。"""

from typing import Protocol

from app.domain.entities.wardrobe_item import (
    WardrobeItem,
    WardrobeItemStatus,
)


class WardrobeRepository(Protocol):
    """定义用户衣橱的持久化和查询能力。"""

    async def get_by_id(
        self,
        user_id: str,
        wardrobe_item_id: str,
    ) -> WardrobeItem | None:
        """查询属于指定用户的一件衣橱单品。"""

        ...

    async def search(
        self,
        user_id: str,
        category: str | None = None,
        status: WardrobeItemStatus | None = None,
        limit: int = 100,
    ) -> list[WardrobeItem]:
        """根据用户、品类和状态查询衣橱单品。"""

        ...

    async def save(
        self,
        item: WardrobeItem,
    ) -> WardrobeItem:
        """新增或更新一件衣橱单品。"""

        ...

    async def delete(
        self,
        user_id: str,
        wardrobe_item_id: str,
    ) -> bool:
        """删除指定用户的一件衣橱单品。"""

        ...