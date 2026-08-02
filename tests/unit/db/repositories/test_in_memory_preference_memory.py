"""长期偏好审计内存仓库测试。"""

from datetime import UTC, datetime

import pytest

from app.db.repositories.in_memory_preference_memory import (
    InMemoryPreferenceMemoryRepository,
)
from app.domain.entities.preference_candidate import (
    PreferenceCandidateCategory,
    PreferenceDirection,
)
from app.domain.entities.preference_memory import (
    PreferenceMemory,
    PreferenceMemorySource,
)


def _memory(
    user_id: str = "user-001",
    value: str = "休闲",
) -> PreferenceMemory:
    """创建内存仓库测试记录。"""

    confirmed_at = datetime(
        2026,
        8,
        2,
        10,
        tzinfo=UTC,
    )
    return PreferenceMemory(
        preference_memory_id=(
            "pm_0123456789abcdef0123456789abcdef"
        ),
        user_id=user_id,
        category=PreferenceCandidateCategory.STYLE,
        value=value,
        direction=PreferenceDirection.PREFER,
        source=(
            PreferenceMemorySource.OUTFIT_FEEDBACK_CONFIRMATION
        ),
        source_reference_ids=("outfit-001",),
        confirmed_at=confirmed_at,
        last_confirmed_at=confirmed_at,
    )


@pytest.mark.anyio
async def test_in_memory_repository_uses_normalized_identity() -> None:
    """验证大小写和空白变化不会创建重复业务记录。"""

    repository = InMemoryPreferenceMemoryRepository()
    memory = _memory(value=" Casual ")
    await repository.save(memory)

    found = await repository.get_by_identity(
        "user-001",
        PreferenceCandidateCategory.STYLE,
        "casual",
    )

    assert found == memory


@pytest.mark.anyio
async def test_in_memory_repository_lists_and_deletes_one_user() -> None:
    """验证列表和删除操作保持用户隔离。"""

    first = _memory()
    second = _memory(
        user_id="user-002",
        value="简约",
    ).model_copy(
        update={
            "preference_memory_id": (
                "pm_fedcba9876543210fedcba9876543210"
            ),
        },
    )
    repository = InMemoryPreferenceMemoryRepository(
        (first, second),
    )

    assert await repository.list_by_user_id(
        "user-001",
    ) == (first,)
    assert await repository.delete_by_user_id(
        "user-001",
    ) == 1
    assert await repository.list_by_user_id(
        "user-001",
    ) == ()
    assert await repository.list_by_user_id(
        "user-002",
    ) == (second,)


@pytest.mark.anyio
async def test_in_memory_repository_gets_and_deletes_by_id() -> None:
    """验证单条操作校验用户归属并保持幂等。"""

    memory = _memory()
    repository = InMemoryPreferenceMemoryRepository(
        (memory,),
    )

    assert await repository.get_by_id(
        "user-002",
        memory.preference_memory_id,
    ) is None
    assert await repository.get_by_id(
        "user-001",
        memory.preference_memory_id,
    ) == memory
    assert await repository.delete_by_id(
        "user-001",
        memory.preference_memory_id,
    ) is True
    assert await repository.delete_by_id(
        "user-001",
        memory.preference_memory_id,
    ) is False
