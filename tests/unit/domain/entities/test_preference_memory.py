"""已确认长期偏好审计实体测试。"""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.domain.entities.preference_candidate import (
    PreferenceCandidateCategory,
    PreferenceDirection,
)
from app.domain.entities.preference_memory import (
    PreferenceMemory,
    PreferenceMemorySource,
    create_preference_memory_id,
)


def _memory(
    *,
    expires_at: datetime | None = None,
) -> PreferenceMemory:
    """创建测试使用的已确认偏好。"""

    confirmed_at = datetime(
        2026,
        8,
        2,
        10,
        tzinfo=UTC,
    )
    return PreferenceMemory(
        preference_memory_id=(
            create_preference_memory_id()
        ),
        user_id="user-001",
        category=PreferenceCandidateCategory.STYLE,
        value=" 休闲 ",
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
        expires_at=expires_at,
    )


def test_preference_memory_normalizes_value_and_tracks_source() -> None:
    """验证记录保留来源、证据和规范显示值。"""

    memory = _memory()

    assert memory.value == "休闲"
    assert memory.source_reference_ids == (
        "outfit-001",
        "outfit-002",
    )
    assert memory.is_active(
        datetime(2026, 8, 3, tzinfo=UTC),
    )


def test_preference_memory_can_expire() -> None:
    """验证可选过期时间控制长期偏好是否进入当前上下文。"""

    expires_at = datetime(
        2026,
        8,
        5,
        tzinfo=UTC,
    )
    memory = _memory(expires_at=expires_at)

    assert memory.is_active(
        expires_at - timedelta(seconds=1),
    )
    assert not memory.is_active(expires_at)


def test_preference_memory_rejects_naive_audit_time() -> None:
    """验证不带时区的确认时间不能写入审计记录。"""

    with pytest.raises(
        ValidationError,
        match="必须包含时区",
    ):
        PreferenceMemory(
            preference_memory_id=(
                create_preference_memory_id()
            ),
            user_id="user-001",
            category=PreferenceCandidateCategory.STYLE,
            value="休闲",
            direction=PreferenceDirection.PREFER,
            source=(
                PreferenceMemorySource.OUTFIT_FEEDBACK_CONFIRMATION
            ),
            source_reference_ids=("outfit-001",),
            confirmed_at=datetime(2026, 8, 2, 10),  # noqa: DTZ001
            last_confirmed_at=datetime(2026, 8, 2, 10),  # noqa: DTZ001
        )
