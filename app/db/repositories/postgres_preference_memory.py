"""已确认长期偏好审计的 PostgreSQL 仓库。"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.mappers.preference_memory import (
    preference_memory_entity_to_model,
    preference_memory_model_to_entity,
)
from app.db.models.preference_memory import (
    PreferenceMemoryModel,
)
from app.domain.entities.preference_candidate import (
    PreferenceCandidateCategory,
)
from app.domain.entities.preference_memory import (
    PreferenceMemory,
    normalize_preference_memory_value,
)


class PostgresPreferenceMemoryRepository:
    """使用请求级 AsyncSession 持久化偏好审计。"""

    def __init__(self, session: AsyncSession) -> None:
        """保存当前请求共享的数据库 Session。"""

        self._session = session

    async def get_by_id(
        self,
        user_id: str,
        preference_memory_id: str,
    ) -> PreferenceMemory | None:
        """按用户和记录 ID 读取，避免跨用户访问。"""

        statement = select(
            PreferenceMemoryModel,
        ).where(
            PreferenceMemoryModel.user_id == user_id,
            PreferenceMemoryModel.preference_memory_id
            == preference_memory_id,
        )
        result = await self._session.execute(statement)
        memory_model = result.scalar_one_or_none()
        if memory_model is None:
            return None
        return preference_memory_model_to_entity(
            memory_model,
        )

    async def get_by_identity(
        self,
        user_id: str,
        category: PreferenceCandidateCategory,
        value: str,
    ) -> PreferenceMemory | None:
        """按用户、类别和规范化值读取记录。"""

        statement = select(
            PreferenceMemoryModel,
        ).where(
            PreferenceMemoryModel.user_id == user_id,
            PreferenceMemoryModel.category
            == category.value,
            PreferenceMemoryModel.normalized_value
            == normalize_preference_memory_value(value),
        )
        result = await self._session.execute(statement)
        memory_model = result.scalar_one_or_none()
        if memory_model is None:
            return None
        return preference_memory_model_to_entity(
            memory_model,
        )

    async def list_by_user_id(
        self,
        user_id: str,
    ) -> tuple[PreferenceMemory, ...]:
        """稳定排序读取当前用户全部审计记录。"""

        statement = (
            select(PreferenceMemoryModel)
            .where(
                PreferenceMemoryModel.user_id
                == user_id,
            )
            .order_by(
                PreferenceMemoryModel.category,
                PreferenceMemoryModel.normalized_value,
            )
        )
        result = await self._session.execute(statement)
        return tuple(
            preference_memory_model_to_entity(model)
            for model in result.scalars().all()
        )

    async def save(
        self,
        memory: PreferenceMemory,
    ) -> PreferenceMemory:
        """在请求事务中新增或更新记录。"""

        await self._session.merge(
            preference_memory_entity_to_model(memory),
        )
        await self._session.flush()
        return memory

    async def delete_by_user_id(
        self,
        user_id: str,
    ) -> int:
        """删除当前用户全部偏好审计记录。"""

        statement = select(
            PreferenceMemoryModel,
        ).where(
            PreferenceMemoryModel.user_id == user_id,
        )
        result = await self._session.execute(statement)
        models = tuple(result.scalars().all())
        for model in models:
            await self._session.delete(model)
        if models:
            await self._session.flush()
        return len(models)

    async def delete_by_id(
        self,
        user_id: str,
        preference_memory_id: str,
    ) -> bool:
        """删除当前用户的一条记录，并保持幂等。"""

        statement = select(
            PreferenceMemoryModel,
        ).where(
            PreferenceMemoryModel.user_id == user_id,
            PreferenceMemoryModel.preference_memory_id
            == preference_memory_id,
        )
        result = await self._session.execute(statement)
        memory_model = result.scalar_one_or_none()
        if memory_model is None:
            return False
        await self._session.delete(memory_model)
        await self._session.flush()
        return True
