"""Agent Style Profile 快照测试。"""

from app.agents.schemas.style_profile import (
    StyleProfileSnapshot,
)
from app.domain.entities.style_profile import StyleProfile


def test_snapshot_excludes_internal_user_id() -> None:
    """验证进入 Agent State 的快照不包含内部用户标识。"""

    snapshot = StyleProfileSnapshot.from_profile(
        StyleProfile(
            user_id="user-001",
            preferred_styles=("简约",),
            avoided_colors=("黑色",),
        ),
    )

    assert snapshot.preferred_styles == ("简约",)
    assert snapshot.avoided_colors == ("黑色",)
    assert "user_id" not in snapshot.model_dump()
