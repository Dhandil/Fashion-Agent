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
