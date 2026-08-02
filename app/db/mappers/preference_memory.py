"""长期偏好审计数据库模型与领域实体转换。"""

from app.db.models.preference_memory import (
    PreferenceMemoryModel,
)
from app.domain.entities.preference_candidate import (
    PreferenceCandidateCategory,
    PreferenceDirection,
)
from app.domain.entities.preference_memory import (
    PreferenceMemory,
    PreferenceMemorySource,
    normalize_preference_memory_value,
)


def preference_memory_entity_to_model(
    memory: PreferenceMemory,
) -> PreferenceMemoryModel:
    """把不可变领域记录转换为 SQLAlchemy 模型。"""

    return PreferenceMemoryModel(
        preference_memory_id=(memory.preference_memory_id),
        user_id=memory.user_id,
        category=memory.category.value,
        value=memory.value,
        normalized_value=(
            normalize_preference_memory_value(
                memory.value,
            )
        ),
        direction=memory.direction.value,
        source=memory.source.value,
        source_reference_ids=list(
            memory.source_reference_ids,
        ),
        confirmed_at=memory.confirmed_at,
        last_confirmed_at=memory.last_confirmed_at,
        expires_at=memory.expires_at,
    )


def preference_memory_model_to_entity(
    memory_model: PreferenceMemoryModel,
) -> PreferenceMemory:
    """把数据库记录恢复成不可变领域实体。"""

    return PreferenceMemory(
        preference_memory_id=(
            memory_model.preference_memory_id
        ),
        user_id=memory_model.user_id,
        category=PreferenceCandidateCategory(
            memory_model.category,
        ),
        value=memory_model.value,
        direction=PreferenceDirection(
            memory_model.direction,
        ),
        source=PreferenceMemorySource(
            memory_model.source,
        ),
        source_reference_ids=tuple(
            memory_model.source_reference_ids,
        ),
        confirmed_at=memory_model.confirmed_at,
        last_confirmed_at=(
            memory_model.last_confirmed_at
        ),
        expires_at=memory_model.expires_at,
    )
