"""PostgreSQL 穿搭方案仓库实现。"""

from collections.abc import Sequence

from sqlalchemy import (
    func,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.mappers.outfit import (
    outfit_entity_to_model,
    outfit_model_to_entity,
)
from app.db.models.outfit import OutfitModel
from app.domain.entities.outfit import Outfit


class PostgresOutfitRepository:
    """使用 SQLAlchemy AsyncSession 持久化穿搭方案。"""

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """保存当前业务操作使用的数据库 Session。"""

        self._session = session

    async def get_by_id(
        self,
        user_id: str,
        outfit_id: str,
    ) -> Outfit | None:
        """查询属于指定用户的一套穿搭方案。"""

        statement = (
            select(OutfitModel)
            .where(
                OutfitModel.user_id == user_id,
                OutfitModel.outfit_id == outfit_id,
            )
            .options(
                # 同时加载穿搭中的全部单品
                selectinload(OutfitModel.items),
            )
        )

        result = await self._session.execute(statement)
        outfit_model = result.scalar_one_or_none()

        if outfit_model is None:
            return None

        return outfit_model_to_entity(outfit_model)

    async def get_by_ids(
        self,
        user_id: str,
        outfit_ids: Sequence[str],
    ) -> list[Outfit]:
        """使用一次查询批量读取当前用户的多套穿搭。"""

        if not outfit_ids:
            return []

        statement = (
            select(OutfitModel)
            .where(
                OutfitModel.user_id == user_id,
                OutfitModel.outfit_id.in_(
                    tuple(outfit_ids),
                ),
            )
            .options(
                selectinload(OutfitModel.items),
            )
        )

        result = await self._session.execute(statement)
        outfit_models = result.scalars().all()
        outfits_by_id = {
            outfit_model.outfit_id: (
                outfit_model_to_entity(outfit_model)
            )
            for outfit_model in outfit_models
        }

        # 数据库 IN 查询不保证顺序，因此按调用方传入的 ID 恢复顺序
        return [
            outfits_by_id[outfit_id]
            for outfit_id in outfit_ids
            if outfit_id in outfits_by_id
        ]

    async def search(
        self,
        user_id: str,
        scenario: str | None = None,
        favorite_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Outfit]:
        """根据用户、场景和收藏状态查询穿搭方案。"""

        # user_id 是所有查询必须具备的隔离条件
        statement = (
            select(OutfitModel)
            .where(
                OutfitModel.user_id == user_id,
            )
            .options(
                selectinload(OutfitModel.items),
            )
        )

        # 用户提供场景时执行精确过滤
        if scenario is not None:
            statement = statement.where(
                OutfitModel.scenario == scenario,
            )

        # favorite_only 为 True 时只查询收藏方案
        if favorite_only:
            statement = statement.where(
                OutfitModel.is_favorite.is_(True),
            )

        # 最近更新的方案排在前面
        statement = statement.order_by(
            OutfitModel.updated_at.desc(),
            OutfitModel.outfit_id.asc(),
        ).offset(offset).limit(limit)

        result = await self._session.execute(statement)
        outfit_models = result.scalars().all()

        return [
            outfit_model_to_entity(outfit_model)
            for outfit_model in outfit_models
        ]

    async def count(
        self,
        user_id: str,
        scenario: str | None = None,
        favorite_only: bool = False,
    ) -> int:
        """统计符合用户和过滤条件的穿搭数量。"""

        statement = select(
            func.count(),
        ).select_from(
            OutfitModel,
        ).where(
            OutfitModel.user_id == user_id,
        )

        if scenario is not None:
            statement = statement.where(
                OutfitModel.scenario == scenario,
            )

        if favorite_only:
            statement = statement.where(
                OutfitModel.is_favorite.is_(True),
            )

        result = await self._session.execute(statement)

        return result.scalar_one()

    async def save(
        self,
        outfit: Outfit,
    ) -> Outfit:
        """新增或更新一套穿搭方案。"""

        outfit_model = outfit_entity_to_model(outfit)

        # merge 根据复合主键判断数据是新增还是更新
        # 子单品会通过 relationship 的级联规则一起处理
        await self._session.merge(outfit_model)

        # flush 把当前变更发送给数据库，但不提交事务
        await self._session.flush()

        return outfit

    async def delete(
        self,
        user_id: str,
        outfit_id: str,
    ) -> bool:
        """删除属于指定用户的一套穿搭方案。"""

        statement = (
            select(OutfitModel)
            .where(
                OutfitModel.user_id == user_id,
                OutfitModel.outfit_id == outfit_id,
            )
            .options(
                selectinload(OutfitModel.items),
            )
        )

        result = await self._session.execute(statement)
        outfit_model = result.scalar_one_or_none()

        if outfit_model is None:
            return False

        # 删除主记录时，子单品会按照级联规则一起删除
        await self._session.delete(outfit_model)
        await self._session.flush()

        return True
