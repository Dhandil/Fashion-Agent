"""衣橱候选选择策略测试。"""

from app.domain.entities.weather import WeatherContext
from app.domain.policies.wardrobe_candidates import (
    WardrobeCandidateExclusionReason,
    select_eligible_wardrobe_records,
)


def test_unavailable_item_is_excluded_without_extra_statuses() -> None:
    """验证清洗或未干统一标记不可用后不会进入模型候选。"""

    selection = select_eligible_wardrobe_records(
        (
            {
                "wardrobe_item_id": "shirt-ready",
                "name": "白色衬衫",
                "status": "available",
            },
            {
                "wardrobe_item_id": "shirt-drying",
                "name": "浅蓝衬衫",
                "status": "unavailable",
                "notes": "刚洗完，还没有晾干",
            },
        ),
    )

    assert [record["wardrobe_item_id"] for record in selection.eligible_records] == ["shirt-ready"]
    assert selection.exclusions[0].wardrobe_item_id == ("shirt-drying")
    assert selection.exclusions[0].reason is (WardrobeCandidateExclusionReason.UNAVAILABLE)


def test_high_heat_excludes_obviously_heavy_item() -> None:
    """验证高温候选不包含明显厚重保暖单品。"""

    weather = WeatherContext(
        location="上海",
        target_date="2026-08-02",
        temperature_max_c=35,
        feels_like_c=38,
        source="user_provided",
    )
    selection = select_eligible_wardrobe_records(
        (
            {
                "wardrobe_item_id": "linen-shirt",
                "name": "亚麻衬衫",
                "materials": ["亚麻"],
                "status": "available",
            },
            {
                "wardrobe_item_id": "wool-coat",
                "name": "通勤外套",
                "materials": ["厚羊毛"],
                "status": "available",
            },
        ),
        weather=weather,
    )

    assert [record["wardrobe_item_id"] for record in selection.eligible_records] == ["linen-shirt"]
    assert selection.exclusions[0].reason is (WardrobeCandidateExclusionReason.HOT_WEATHER_CONFLICT)


def test_mild_weather_keeps_available_outerwear() -> None:
    """验证温和天气不会无依据删除用户真实衣物。"""

    weather = WeatherContext(
        location="北京",
        target_date="2026-10-10",
        temperature_max_c=18,
        source="user_provided",
    )
    record = {
        "wardrobe_item_id": "wool-coat",
        "name": "羊毛大衣",
        "status": "available",
    }

    selection = select_eligible_wardrobe_records(
        (record,),
        weather=weather,
    )

    assert selection.eligible_records == (record,)
    assert selection.exclusions == ()


def test_current_avoidances_exclude_structured_preferences() -> None:
    """验证当前轮颜色、材质和风格避免项会筛掉对应候选。"""

    selection = select_eligible_wardrobe_records(
        (
            {
                "wardrobe_item_id": "safe-shirt",
                "name": "米白衬衫",
                "colors": ["米白"],
                "materials": ["棉"],
                "style_tags": ["简约"],
                "status": "available",
            },
            {
                "wardrobe_item_id": "wool-shirt",
                "name": "混纺衬衫",
                "materials": ["羊毛混纺"],
                "status": "available",
            },
            {
                "wardrobe_item_id": "black-shirt",
                "name": "深色衬衫",
                "colors": ["黑色"],
                "status": "available",
            },
            {
                "wardrobe_item_id": "street-shirt",
                "name": "印花衬衫",
                "style_tags": ["街头风"],
                "status": "available",
            },
        ),
        avoided_materials=("羊毛",),
        avoided_colors=("黑色",),
        avoided_styles=("街头风",),
    )

    assert [record["wardrobe_item_id"] for record in selection.eligible_records] == ["safe-shirt"]
    assert {exclusion.reason for exclusion in selection.exclusions} == {
        WardrobeCandidateExclusionReason.AVOIDED_MATERIAL,
        WardrobeCandidateExclusionReason.AVOIDED_COLOR,
        WardrobeCandidateExclusionReason.AVOIDED_STYLE,
    }
