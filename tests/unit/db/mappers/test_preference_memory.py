"""长期偏好审计数据库转换测试。"""

from datetime import UTC, datetime

from app.db.mappers.preference_memory import (
    preference_memory_entity_to_model,
    preference_memory_model_to_entity,
)
from app.domain.entities.preference_candidate import (
    PreferenceCandidateCategory,
    PreferenceDirection,
)
from app.domain.entities.preference_memory import (
    PreferenceMemory,
    PreferenceMemorySource,
)


def _memory() -> PreferenceMemory:
    """创建固定的审计记录。"""

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
        user_id="user-001",
        category=PreferenceCandidateCategory.STYLE,
        value="休闲",
        direction=PreferenceDirection.PREFER,
        source=(
            PreferenceMemorySource.OUTFIT_FEEDBACK_CONFIRMATION
        ),
        source_reference_ids=(
            "outfit-001",
            "outfit-002",
        ),
        confirmed_at=confirmed_at,
        last_confirmed_at=confirmed_at,
    )


def test_preference_memory_mapper_preserves_audit_data() -> None:
    """验证数据库转换保留来源、证据和确认时间。"""

    memory = _memory()
    model = preference_memory_entity_to_model(memory)

    assert model.normalized_value == "休闲"
    assert model.source_reference_ids == [
        "outfit-001",
        "outfit-002",
    ]
    assert preference_memory_model_to_entity(model) == memory
