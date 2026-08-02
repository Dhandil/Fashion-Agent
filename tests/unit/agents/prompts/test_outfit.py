"""结构化 Outfit 提示词边界测试。"""

from app.agents.prompts.outfit import OUTFIT_GENERATION_SYSTEM_PROMPT
from app.agents.prompts.outfit_correction import (
    OUTFIT_CORRECTION_SYSTEM_PROMPT,
)


def test_generation_prompt_treats_weather_guidance_as_constraint() -> None:
    """验证高温限制不会被表达成普通可选建议。"""

    assert "weather_outfit_guidance 是" in OUTFIT_GENERATION_SYSTEM_PROMPT
    assert "不是可选建议" in OUTFIT_GENERATION_SYSTEM_PROMPT
    assert "厚羊毛大衣" in OUTFIT_GENERATION_SYSTEM_PROMPT


def test_correction_prompt_requires_issue_elimination() -> None:
    """验证修正必须消除错误，而不是只改文字说明。"""

    assert "消除错误的优先级高于保留原方案" in (OUTFIT_CORRECTION_SYSTEM_PROMPT)
    assert "hot_weather_conflict" in OUTFIT_CORRECTION_SYSTEM_PROMPT
    assert "删除或替换" in OUTFIT_CORRECTION_SYSTEM_PROMPT


def test_generation_prompt_treats_current_avoidances_as_hard_constraints() -> None:
    """验证当前轮避雷项优先于历史偏好和原方案。"""

    assert "avoided_styles" in OUTFIT_GENERATION_SYSTEM_PROMPT
    assert "当前轮明确约束" in OUTFIT_GENERATION_SYSTEM_PROMPT
    assert "高于 Style Profile" in OUTFIT_GENERATION_SYSTEM_PROMPT


def test_correction_prompt_requires_avoidance_conflicts_removed() -> None:
    """验证修正节点认识三类稳定避雷错误码。"""

    for issue_code in (
        "avoided_style",
        "avoided_color",
        "avoided_material",
    ):
        assert issue_code in OUTFIT_CORRECTION_SYSTEM_PROMPT
    assert "不得通过改写单品名称隐藏冲突" in OUTFIT_CORRECTION_SYSTEM_PROMPT


def test_outfit_prompts_use_resolved_style_constraints() -> None:
    """验证生成和修正使用相同的确定性偏好合并结果。"""

    assert "effective_style_constraints" in (OUTFIT_GENERATION_SYSTEM_PROMPT)
    assert "effective_style_constraints" in (OUTFIT_CORRECTION_SYSTEM_PROMPT)
    assert "历史反馈不得覆盖" in (OUTFIT_GENERATION_SYSTEM_PROMPT)
    assert "当前明确要求 > 长期档案" in (OUTFIT_CORRECTION_SYSTEM_PROMPT)
