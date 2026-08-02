"""根据当前真实候选判断能否组成完整 Outfit。"""

from collections.abc import Mapping, Sequence
from typing import Any

from app.agents.schemas.requirements import (
    OutfitRequirementAnalysis,
    RequestIntent,
    ShoppingIntent,
)
from app.domain.entities.outfit import WardrobeGap
from app.domain.entities.outfit_gap import (
    CoreOutfitRole,
    OutfitGapNextAction,
    OutfitGapReport,
)

_UPPER_TERMS = (
    "上装",
    "上衣",
    "衬衫",
    "针织衫",
    "毛衣",
    "卫衣",
    "t恤",
)
_LOWER_TERMS = (
    "下装",
    "裤",
    "半身裙",
)
_ONE_PIECE_TERMS = (
    "连衣裙",
    "连体",
)
_FOOTWEAR_TERMS = (
    "鞋履",
    "鞋",
)


def _record_text(
    record: Mapping[str, Any],
) -> str:
    """拼接用于角色识别的有限结构化字段。"""

    return " ".join(
        value
        for field_name in (
            "role",
            "category",
            "name",
        )
        if isinstance(
            value := record.get(field_name),
            str,
        )
    ).casefold()


def _contains_any(
    text: str,
    terms: Sequence[str],
) -> bool:
    """判断候选说明是否包含任一稳定角色词。"""

    return any(term in text for term in terms)


def find_missing_core_roles(
    records: Sequence[Mapping[str, Any]],
) -> tuple[CoreOutfitRole, ...]:
    """返回当前衣橱和商品候选没有覆盖的核心角色。"""

    texts = tuple(_record_text(record) for record in records)
    has_one_piece = any(_contains_any(text, _ONE_PIECE_TERMS) for text in texts)
    has_upper = has_one_piece or any(_contains_any(text, _UPPER_TERMS) for text in texts)
    has_lower = has_one_piece or any(_contains_any(text, _LOWER_TERMS) for text in texts)
    has_footwear = any(_contains_any(text, _FOOTWEAR_TERMS) for text in texts)

    return tuple(
        role
        for role, is_covered in (
            (CoreOutfitRole.UPPER, has_upper),
            (CoreOutfitRole.LOWER, has_lower),
            (CoreOutfitRole.FOOTWEAR, has_footwear),
        )
        if not is_covered
    )


def _gap_for_role(
    role: CoreOutfitRole,
) -> WardrobeGap:
    """为缺失角色生成不指向商品的普通建议。"""

    suggestions = {
        CoreOutfitRole.UPPER: "适合当前场景的上装",
        CoreOutfitRole.LOWER: "适合当前场景的下装",
        CoreOutfitRole.FOOTWEAR: "适合当前场景的鞋履",
    }
    return WardrobeGap(
        role=role.value,
        suggested_item=suggestions[role],
        reason=(f"当前可用衣橱和已授权商品结果中没有可用于完整搭配的{role.value}。"),
    )


def build_outfit_gap_report(
    *,
    analysis: OutfitRequirementAnalysis | None,
    wardrobe_records: Sequence[Mapping[str, Any]],
    product_records: Sequence[Mapping[str, Any]],
) -> OutfitGapReport | None:
    """需要真实衣橱且核心角色不足时生成确定性缺口报告。"""

    if (
        analysis is None
        or analysis.intent
        not in {
            RequestIntent.OUTFIT,
            RequestIntent.OUTFIT_ADJUSTMENT,
            RequestIntent.SHOPPING,
        }
        or not analysis.needs_wardrobe
    ):
        return None

    usable_products = tuple(
        record for record in product_records if record.get("in_stock") is not False
    )
    missing_roles = find_missing_core_roles(
        (
            *wardrobe_records,
            *usable_products,
        ),
    )
    if not missing_roles:
        return None

    shopping_allowed = analysis.shopping_intent is ShoppingIntent.EXPLICIT
    next_actions = [
        OutfitGapNextAction.ADD_WARDROBE_ITEMS,
        OutfitGapNextAction.ADJUST_REQUIREMENTS,
    ]
    if shopping_allowed:
        next_actions.append(
            OutfitGapNextAction.SEARCH_PRODUCTS,
        )

    return OutfitGapReport(
        missing_roles=missing_roles,
        gaps=tuple(_gap_for_role(role) for role in missing_roles),
        shopping_search_allowed=shopping_allowed,
        next_actions=tuple(next_actions),
        reason=("当前真实可用候选不足以组成包含核心角色的完整穿搭。"),
    )


def render_outfit_gap_message(
    report: OutfitGapReport,
) -> str:
    """生成不会暗示已购物或已拥有单品的用户说明。"""

    missing_roles = "、".join(role.value for role in report.missing_roles)
    if report.shopping_search_allowed:
        next_step = "你可以调整商品条件后继续查询，也可以补充衣橱单品或放宽本轮要求。"
    else:
        next_step = (
            "本轮没有获得商品搜索授权，我不会自动查询商品。"
            "你可以补充衣橱单品、调整要求，"
            "或明确告诉我是否需要查找商品。"
        )
    return f"当前可用数据还不能组成完整穿搭，缺少：{missing_roles}。{next_step}"
