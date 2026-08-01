"""结构化穿搭需求模型测试。"""

import pytest
from pydantic import ValidationError

from app.agents.schemas.requirements import (
    OutfitRequirementAnalysis,
    RequestIntent,
    RequirementField,
)


def test_requirement_analysis_accepts_minimal_missing_fields() -> None:
    """验证需求不足时可以保存有限的标准缺失字段。"""

    analysis = OutfitRequirementAnalysis(
        intent=RequestIntent.OUTFIT,
        is_sufficient=False,
        missing_fields=(
            RequirementField.SCENARIO,
            RequirementField.LOCATION,
        ),
    )

    assert analysis.missing_fields == (
        RequirementField.SCENARIO,
        RequirementField.LOCATION,
    )


def test_requirement_analysis_rejects_inconsistent_sufficiency() -> None:
    """验证充分度和缺失字段不能互相矛盾。"""

    with pytest.raises(ValidationError):
        OutfitRequirementAnalysis(
            intent=RequestIntent.OUTFIT,
            is_sufficient=True,
            missing_fields=(RequirementField.SCENARIO,),
        )


def test_requirement_analysis_limits_missing_questions() -> None:
    """验证单轮最多追问三个必要字段。"""

    with pytest.raises(ValidationError):
        OutfitRequirementAnalysis(
            intent=RequestIntent.OUTFIT,
            is_sufficient=False,
            missing_fields=(
                RequirementField.SCENARIO,
                RequirementField.LOCATION,
                RequirementField.TARGET_DATE,
                RequirementField.STYLE,
            ),
        )
