"""已确认长期偏好审计仓库接口。"""

from typing import Protocol

from app.domain.entities.preference_candidate import (
    PreferenceCandidateCategory,
)
from app.domain.entities.preference_memory import (
    PreferenceMemory,
)


class PreferenceMemoryRepository(Protocol):
    """定义已确认偏好的持久化和用户删除能力。"""

    async def get_by_id(
        self,
        user_id: str,
        preference_memory_id: str,
    ) -> PreferenceMemory | None:
        """按用户和记录 ID 读取，避免跨用户访问。"""

        ...

    async def get_by_identity(
        self,
        user_id: str,
        category: PreferenceCandidateCategory,
        value: str,
    ) -> PreferenceMemory | None:
        """按用户、类别和规范化值读取记录。"""

        ...

    async def list_by_user_id(
        self,
        user_id: str,
    ) -> tuple[PreferenceMemory, ...]:
        """读取当前用户的全部审计记录。"""

        ...

    async def save(
        self,
        memory: PreferenceMemory,
    ) -> PreferenceMemory:
        """新增或更新一条已确认偏好。"""

        ...

    async def delete_by_user_id(
        self,
        user_id: str,
    ) -> int:
        """删除当前用户全部审计记录并返回数量。"""

        ...

    async def delete_by_id(
        self,
        user_id: str,
        preference_memory_id: str,
    ) -> bool:
        """删除当前用户的一条审计记录。"""

        ...
