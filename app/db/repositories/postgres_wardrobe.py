"""PostgreSQL 用户衣橱仓库实现。"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.mappers.wardrobe_item import (
    wardrobe_item_entity_to_model,
    wardrobe_item_model_to_entity,
)
from app.db.models.wardrobe_item import (
    WardrobeItemModel,
)
from app.domain.entities.wardrobe_item import (
    WardrobeItem,
    WardrobeItemStatus,
)


class PostgresWardrobeRepository:
    """使用 SQLAlchemy AsyncSession 持久化用户衣橱。"""

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """保存当前业务操作使用的数据库 Session。"""

        self._session = session

    async def get_by_id(
        self,
        user_id: str,
        wardrobe_item_id: str,
    ) -> WardrobeItem | None:
        """查询属于指定用户的一件衣橱单品。"""

        statement = select(
            WardrobeItemModel,
        ).where(
            WardrobeItemModel.user_id == user_id,
            WardrobeItemModel.wardrobe_item_id
            == wardrobe_item_id,
        )

        result = await self._session.execute(statement)
        item_model = result.scalar_one_or_none()

        if item_model is None:
            return None

        return wardrobe_item_model_to_entity(
            item_model,
        )

    async def search(
        self,
        user_id: str,
        category: str | None = None,
        status: WardrobeItemStatus | None = None,
        limit: int = 100,
    ) -> list[WardrobeItem]:
        """根据用户、品类和状态查询衣橱单品。"""

        # 所有衣橱查询必须包含用户隔离条件
        statement = select(
            WardrobeItemModel,
        ).where(
            WardrobeItemModel.user_id == user_id,
        )

        if category is not None:
            statement = statement.where(
                WardrobeItemModel.category == category,
            )

        if status is not None:
            statement = statement.where(
                WardrobeItemModel.status
                == status.value,
            )

        # 最近更新的衣物优先返回
        statement = statement.order_by(
            WardrobeItemModel.updated_at.desc(),
            WardrobeItemModel.wardrobe_item_id.asc(),
        ).limit(limit)

        result = await self._session.execute(statement)
        item_models = result.scalars().all()

        return [
            wardrobe_item_model_to_entity(item_model)
            for item_model in item_models
        ]

    async def save(
        self,
        item: WardrobeItem,
    ) -> WardrobeItem:
        """新增或更新一件衣橱单品。"""

        item_model = wardrobe_item_entity_to_model(
            item,
        )

        # 复合主键用于判断新增或更新
        await self._session.merge(item_model)
        await self._session.flush()

        return item

    async def delete(
        self,
        user_id: str,
        wardrobe_item_id: str,
    ) -> bool:
        """删除属于指定用户的一件衣橱单品。"""

        statement = select(
            WardrobeItemModel,
        ).where(
            WardrobeItemModel.user_id == user_id,
            WardrobeItemModel.wardrobe_item_id
            == wardrobe_item_id,
        )

        result = await self._session.execute(statement)
        item_model = result.scalar_one_or_none()

        if item_model is None:
            return False

        await self._session.delete(item_model)
        await self._session.flush()

        return True