"""用户穿搭档案的内存仓库实现。"""

from collections.abc import Iterable

from app.domain.entities.style_profile import StyleProfile


class InMemoryStyleProfileRepository:
    """在当前 Python 进程内保存用户穿搭档案。"""

    def __init__(
        self,
        profiles: Iterable[StyleProfile] | None = None,
    ) -> None:
        """使用可选的初始档案创建内存仓库。"""

        # 使用 user_id 作为键，保证每个用户只有一份当前档案
        self._profiles = {
            profile.user_id: profile
            for profile in profiles or ()
        }

    async def get_by_user_id(
        self,
        user_id: str,
    ) -> StyleProfile | None:
        """根据用户 ID 查询穿搭档案。"""

        return self._profiles.get(user_id)

    async def save(
        self,
        profile: StyleProfile,
    ) -> StyleProfile:
        """新增或替换用户当前的穿搭档案。"""

        # 相同 user_id 再次保存时替换旧版本
        self._profiles[profile.user_id] = profile

        return profile

    async def delete_by_user_id(
        self,
        user_id: str,
    ) -> bool:
        """删除用户档案并返回档案是否原本存在。"""

        deleted_profile = self._profiles.pop(
            user_id,
            None,
        )

        return deleted_profile is not None