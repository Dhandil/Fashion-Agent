"""加载近期已保存 Outfit 的上下文节点。"""

from collections.abc import Awaitable, Callable, Sequence

from app.agents.state.shopping import ShoppingAgentState
from app.domain.entities.outfit import Outfit, OutfitItemSource
from app.domain.repositories.outfit import OutfitRepository

DEFAULT_RECENT_OUTFIT_LIMIT = 5


def build_recent_outfits_context(
    outfits: Sequence[Outfit],
) -> str:
    """把近期 Outfit 整理成用于减少重复的有限上下文。"""

    context_records: list[str] = []

    for outfit in outfits:
        item_records: list[str] = []

        for item in outfit.items:
            source_reference = ""

            if (
                item.source
                is OutfitItemSource.WARDROBE
                and item.source_reference_id
            ):
                source_reference = (
                    f"（衣橱 ID："
                    f"{item.source_reference_id}）"
                )

            item_records.append(
                f"{item.role}：{item.name}"
                f"{source_reference}",
            )

        style_tags = "、".join(
            outfit.style_tags,
        ) or "未标注"
        items = "；".join(item_records) or "未记录"

        context_records.append(
            (
                f"- 近期穿搭：{outfit.name}；"
                f"场景：{outfit.scenario}；"
                f"风格：{style_tags}；"
                f"单品组合：{items}"
            ),
        )

    return "\n".join(context_records)


def create_load_recent_outfits_node(
    repository: OutfitRepository,
    user_id: str,
    limit: int = DEFAULT_RECENT_OUTFIT_LIMIT,
) -> Callable[
    [ShoppingAgentState],
    Awaitable[dict[str, str]],
]:
    """创建绑定当前用户的近期 Outfit 加载节点。"""

    async def load_recent_outfits(
        _state: ShoppingAgentState,
    ) -> dict[str, str]:
        """读取近期 Outfit，并生成防重复参考上下文。"""

        outfits = await repository.search(
            user_id=user_id,
            scenario=None,
            favorite_only=False,
            limit=limit,
            offset=0,
        )

        return {
            "recent_outfits_context": (
                build_recent_outfits_context(outfits)
            ),
        }

    return load_recent_outfits
