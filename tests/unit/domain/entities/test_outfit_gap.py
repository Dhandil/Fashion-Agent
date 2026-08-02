"""结构化 Outfit 缺口实体测试。"""

import pytest
from pydantic import ValidationError

from app.domain.entities.outfit import WardrobeGap
from app.domain.entities.outfit_gap import (
    CoreOutfitRole,
    OutfitGapNextAction,
    OutfitGapReport,
)


def _gap(role: CoreOutfitRole) -> WardrobeGap:
    """创建与核心角色对应的最小衣橱缺口。"""

    return WardrobeGap(
        role=role.value,
        suggested_item=f"适合场景的{role.value}",
        reason=f"当前缺少{role.value}。",
    )


def test_gap_report_accepts_consistent_roles_and_actions() -> None:
    """验证角色、缺口和下一步一致时可以创建报告。"""

    report = OutfitGapReport(
        missing_roles=(CoreOutfitRole.LOWER,),
        gaps=(_gap(CoreOutfitRole.LOWER),),
        shopping_search_allowed=False,
        next_actions=(OutfitGapNextAction.ADD_WARDROBE_ITEMS,),
        reason="当前真实候选不足以形成完整穿搭。",
    )

    assert report.missing_roles == (CoreOutfitRole.LOWER,)


def test_gap_report_rejects_mismatched_gap_roles() -> None:
    """验证缺口明细不能描述 missing_roles 之外的角色。"""

    with pytest.raises(
        ValidationError,
        match="gaps 必须与 missing_roles 完全对应",
    ):
        OutfitGapReport(
            missing_roles=(CoreOutfitRole.LOWER,),
            gaps=(_gap(CoreOutfitRole.FOOTWEAR),),
            shopping_search_allowed=False,
            next_actions=(OutfitGapNextAction.ADJUST_REQUIREMENTS,),
            reason="当前真实候选不足。",
        )


def test_gap_report_rejects_search_action_without_permission() -> None:
    """验证没有购物授权时不能暴露商品搜索动作。"""

    with pytest.raises(
        ValidationError,
        match="没有购物授权时不能提供商品搜索动作",
    ):
        OutfitGapReport(
            missing_roles=(CoreOutfitRole.FOOTWEAR,),
            gaps=(_gap(CoreOutfitRole.FOOTWEAR),),
            shopping_search_allowed=False,
            next_actions=(OutfitGapNextAction.SEARCH_PRODUCTS,),
            reason="当前真实候选不足。",
        )
