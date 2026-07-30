"""PostgreSQL 用户穿搭档案仓库实现。"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.mappers.style_profile import (
    style_profile_entity_to_model,
    style_profile_model_to_entity,
)
from app.db.models.style_profile import (
    StyleProfileModel,
)
from app.domain.entities.style_profile import (
    StyleProfile,
)


class PostgresStyleProfileRepository:
    """使用 SQLAlchemy AsyncSession 持久化用户穿搭档案。"""

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """保存当前业务操作使用的数据库 Session。"""

        self._session = session

    async def get_by_user_id(
        self,
        user_id: str,
    ) -> StyleProfile | None:
        """根据用户 ID 查询当前穿搭档案。"""

        statement = select(
            StyleProfileModel,
        ).where(
            StyleProfileModel.user_id == user_id,
        )

        result = await self._session.execute(statement)
        profile_model = result.scalar_one_or_none()

        if profile_model is None:
            return None

        return style_profile_model_to_entity(
            profile_model,
        )

    async def save(
        self,
        profile: StyleProfile,
    ) -> StyleProfile:
        """新增或更新用户当前穿搭档案。"""

        profile_model = style_profile_entity_to_model(
            profile,
        )

        # user_id 是主键，相同用户再次保存时会合并更新
        await self._session.merge(profile_model)
        await self._session.flush()

        return profile

    async def delete_by_user_id(
        self,
        user_id: str,
    ) -> bool:
        """删除指定用户的穿搭档案。"""

        statement = select(
            StyleProfileModel,
        ).where(
            StyleProfileModel.user_id == user_id,
        )

        result = await self._session.execute(statement)
        profile_model = result.scalar_one_or_none()

        if profile_model is None:
            return False

        await self._session.delete(profile_model)
        await self._session.flush()

        return True