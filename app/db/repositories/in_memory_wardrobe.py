"""用户衣橱的内存仓库实现。"""

from collections.abc import Iterable

from app.domain.entities.wardrobe_item import (
    WardrobeItem,
    WardrobeItemStatus,
)


class InMemoryWardrobeRepository:
    """在当前 Python 进程内保存用户衣橱。"""

    def __init__(
        self,
        items: Iterable[WardrobeItem] | None = None,
    ) -> None:
        """使用可选的衣橱单品初始化仓库。"""

        # 使用用户 ID 和单品 ID 组成复合键
        # 即使不同用户使用相同单品 ID，也不会互相覆盖
        self._items = {
            (
                item.user_id,
                item.wardrobe_item_id,
            ): item
            for item in items or ()
        }

    async def get_by_id(
        self,
        user_id: str,
        wardrobe_item_id: str,
    ) -> WardrobeItem | None:
        """查询属于指定用户的一件衣橱单品。"""

        return self._items.get(
            (
                user_id,
                wardrobe_item_id,
            ),
        )

    async def search(
        self,
        user_id: str,
        category: str | None = None,
        status: WardrobeItemStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[WardrobeItem]:
        """根据用户、品类、状态和分页条件查询衣橱。"""

        matched_items: list[WardrobeItem] = []

        for item in self._items.values():
            # 只允许查询当前用户自己的衣物
            if item.user_id != user_id:
                continue

            # 提供品类时执行精确品类过滤
            if (
                category is not None
                and item.category != category
            ):
                continue

            # 提供状态时只返回对应状态的衣物
            if (
                status is not None
                and item.status is not status
            ):
                continue

            matched_items.append(item)

        return matched_items[
            offset : offset + limit
        ]

    async def count(
        self,
        user_id: str,
        category: str | None = None,
        status: WardrobeItemStatus | None = None,
    ) -> int:
        """统计符合用户、品类和状态条件的衣物数量。"""

        matched_items = await self.search(
            user_id=user_id,
            category=category,
            status=status,
            # 内存仓库用于开发和测试，取完整匹配结果进行计数
            limit=len(self._items),
        )

        return len(matched_items)

    async def save(
        self,
        item: WardrobeItem,
    ) -> WardrobeItem:
        """新增或更新一件衣橱单品。"""

        item_key = (
            item.user_id,
            item.wardrobe_item_id,
        )
        self._items[item_key] = item

        return item

    async def delete(
        self,
        user_id: str,
        wardrobe_item_id: str,
    ) -> bool:
        """删除指定用户的一件衣橱单品。"""

        deleted_item = self._items.pop(
            (
                user_id,
                wardrobe_item_id,
            ),
            None,
        )

        return deleted_item is not None
