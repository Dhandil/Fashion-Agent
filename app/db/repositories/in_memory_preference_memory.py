"""已确认长期偏好审计的内存仓库。"""

from collections.abc import Iterable

from app.domain.entities.preference_candidate import (
    PreferenceCandidateCategory,
)
from app.domain.entities.preference_memory import (
    PreferenceMemory,
    normalize_preference_memory_value,
)


def _memory_key(
    user_id: str,
    category: PreferenceCandidateCategory,
    value: str,
) -> tuple[str, str, str]:
    """创建与数据库唯一约束一致的内存键。"""

    return (
        user_id,
        category.value,
        normalize_preference_memory_value(value),
    )


class InMemoryPreferenceMemoryRepository:
    """在当前 Python 进程中保存偏好审计记录。"""

    def __init__(
        self,
        memories: Iterable[PreferenceMemory] | None = None,
    ) -> None:
        """使用可选初始记录创建仓库。"""

        self._memories = {
            _memory_key(
                memory.user_id,
                memory.category,
                memory.value,
            ): memory
            for memory in memories or ()
        }

    async def get_by_id(
        self,
        user_id: str,
        preference_memory_id: str,
    ) -> PreferenceMemory | None:
        """按用户和记录 ID 读取，隔离其他用户的数据。"""

        return next(
            (
                memory
                for memory in self._memories.values()
                if memory.user_id == user_id
                and memory.preference_memory_id
                == preference_memory_id
            ),
            None,
        )

    async def get_by_identity(
        self,
        user_id: str,
        category: PreferenceCandidateCategory,
        value: str,
    ) -> PreferenceMemory | None:
        """按稳定业务身份读取一条审计记录。"""

        return self._memories.get(
            _memory_key(user_id, category, value),
        )

    async def list_by_user_id(
        self,
        user_id: str,
    ) -> tuple[PreferenceMemory, ...]:
        """稳定排序返回当前用户的全部记录。"""

        return tuple(
            sorted(
                (
                    memory
                    for memory in self._memories.values()
                    if memory.user_id == user_id
                ),
                key=lambda memory: (
                    memory.category.value,
                    memory.value.casefold(),
                ),
            ),
        )

    async def save(
        self,
        memory: PreferenceMemory,
    ) -> PreferenceMemory:
        """按照业务身份新增或替换记录。"""

        self._memories[
            _memory_key(
                memory.user_id,
                memory.category,
                memory.value,
            )
        ] = memory
        return memory

    async def delete_by_user_id(
        self,
        user_id: str,
    ) -> int:
        """删除当前用户全部审计记录。"""

        keys = tuple(
            key
            for key, memory in self._memories.items()
            if memory.user_id == user_id
        )
        for key in keys:
            del self._memories[key]
        return len(keys)

    async def delete_by_id(
        self,
        user_id: str,
        preference_memory_id: str,
    ) -> bool:
        """删除当前用户的一条记录，并保持幂等。"""

        memory = await self.get_by_id(
            user_id=user_id,
            preference_memory_id=preference_memory_id,
        )
        if memory is None:
            return False
        del self._memories[
            _memory_key(
                memory.user_id,
                memory.category,
                memory.value,
            )
        ]
        return True
