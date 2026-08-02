"""完整 Outfit 候选覆盖与缺口报告测试。"""

from app.agents.schemas.requirements import (
    OutfitRequirementAnalysis,
    RequestIntent,
    ShoppingIntent,
)
from app.domain.entities.outfit_gap import (
    CoreOutfitRole,
    OutfitGapNextAction,
)
from app.domain.policies.outfit_coverage import (
    build_outfit_gap_report,
    find_missing_core_roles,
    render_outfit_gap_message,
)


def _analysis(
    shopping_intent: ShoppingIntent = ShoppingIntent.NONE,
) -> OutfitRequirementAnalysis:
    """创建需要使用衣橱的完整穿搭请求。"""

    return OutfitRequirementAnalysis(
        intent=RequestIntent.OUTFIT,
        scenario="通勤",
        needs_wardrobe=True,
        shopping_intent=shopping_intent,
    )


def test_empty_candidates_are_missing_all_core_roles() -> None:
    """验证没有真实候选时明确缺少上装、下装和鞋履。"""

    assert find_missing_core_roles(()) == (
        CoreOutfitRole.UPPER,
        CoreOutfitRole.LOWER,
        CoreOutfitRole.FOOTWEAR,
    )


def test_one_piece_and_shoes_cover_complete_outfit() -> None:
    """验证连衣裙可以同时覆盖上装与下装。"""

    assert (
        find_missing_core_roles(
            (
                {
                    "category": "连衣裙",
                    "name": "通勤连衣裙",
                },
                {
                    "category": "鞋履",
                    "name": "乐福鞋",
                },
            ),
        )
        == ()
    )


def test_product_candidates_can_fill_explicit_shopping_gap() -> None:
    """验证已授权且真实在库商品可以补齐衣橱角色。"""

    report = build_outfit_gap_report(
        analysis=_analysis(
            ShoppingIntent.EXPLICIT,
        ),
        wardrobe_records=(
            {
                "category": "上装",
                "name": "白色衬衫",
            },
            {
                "category": "下装",
                "name": "灰色长裤",
            },
        ),
        product_records=(
            {
                "category": "鞋履",
                "name": "棕色乐福鞋",
                "in_stock": True,
            },
        ),
    )

    assert report is None


def test_gap_without_shopping_permission_does_not_offer_search() -> None:
    """验证普通穿搭缺口不会越权建议已执行商品查询。"""

    report = build_outfit_gap_report(
        analysis=_analysis(),
        wardrobe_records=(
            {
                "category": "上装",
                "name": "白色衬衫",
            },
        ),
        product_records=(),
    )

    assert report is not None
    assert report.missing_roles == (
        CoreOutfitRole.LOWER,
        CoreOutfitRole.FOOTWEAR,
    )
    assert report.shopping_search_allowed is False
    assert OutfitGapNextAction.SEARCH_PRODUCTS not in (report.next_actions)
    assert "不会自动查询商品" in (render_outfit_gap_message(report))


def test_gap_with_explicit_shopping_permission_offers_search() -> None:
    """验证用户明确购物时缺口报告可以给出商品查询选项。"""

    report = build_outfit_gap_report(
        analysis=_analysis(
            ShoppingIntent.EXPLICIT,
        ),
        wardrobe_records=(),
        product_records=(),
    )

    assert report is not None
    assert report.shopping_search_allowed is True
    assert OutfitGapNextAction.SEARCH_PRODUCTS in (report.next_actions)
