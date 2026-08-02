"""长期偏好候选领域测试。"""

from app.domain.entities.preference_candidate import (
    PreferenceCandidateCategory,
    PreferenceDirection,
    create_preference_candidate_id,
)


def test_candidate_id_is_stable_across_evidence_order() -> None:
    """验证相同证据集合不受输入顺序影响。"""

    first = create_preference_candidate_id(
        category=PreferenceCandidateCategory.STYLE,
        value=" 休闲 ",
        direction=PreferenceDirection.PREFER,
        evidence_outfit_ids=("outfit-002", "outfit-001"),
    )
    second = create_preference_candidate_id(
        category=PreferenceCandidateCategory.STYLE,
        value="休闲",
        direction=PreferenceDirection.PREFER,
        evidence_outfit_ids=("outfit-001", "outfit-002"),
    )

    assert first == second
    assert first.startswith("pc_")
    assert len(first) == 35


def test_candidate_id_changes_when_evidence_changes() -> None:
    """验证支持或反向证据变化会使旧候选 ID 失效。"""

    original = create_preference_candidate_id(
        category=PreferenceCandidateCategory.STYLE,
        value="休闲",
        direction=PreferenceDirection.PREFER,
        evidence_outfit_ids=("outfit-001", "outfit-002"),
    )
    changed = create_preference_candidate_id(
        category=PreferenceCandidateCategory.STYLE,
        value="休闲",
        direction=PreferenceDirection.PREFER,
        evidence_outfit_ids=("outfit-001", "outfit-002"),
        opposing_evidence_outfit_ids=("outfit-003",),
    )

    assert changed != original
