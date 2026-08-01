from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class RetrievalEvaluationCase(BaseModel):
    """一条具有稳定预期来源的知识检索问题。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str = Field(min_length=1)
    category: Literal["material", "occasion", "weather", "care"]
    query: str = Field(min_length=1)
    expected_knowledge_id: str = Field(min_length=1)
    expected_section_ids: tuple[str, ...] = Field(
        min_length=1,
    )
    max_rank: int = Field(default=3, gt=0)

    @field_validator("expected_section_ids")
    @classmethod
    def validate_section_ids(
        cls,
        section_ids: tuple[str, ...],
    ) -> tuple[str, ...]:
        """确保评测只引用 S01、S02 等稳定章节编号。"""

        if any(
            len(section_id) != 3 or not section_id.startswith("S") or not section_id[1:].isdigit()
            for section_id in section_ids
        ):
            raise ValueError(
                "expected_section_ids 必须使用 S01、S02 等稳定章节编号。",
            )

        return section_ids


class RetrievalEvaluationSuite(BaseModel):
    """绑定到一次正式知识发布的检索评测问题集。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = Field(min_length=1)
    release_id: str = Field(min_length=1)
    cases: tuple[RetrievalEvaluationCase, ...] = Field(
        min_length=1,
    )

    @model_validator(mode="after")
    def validate_unique_case_ids(
        self,
    ) -> "RetrievalEvaluationSuite":
        """禁止重复 case_id，避免评测报告出现歧义。"""

        case_ids = [case.case_id for case in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("检索评测集中存在重复的 case_id。")

        return self
