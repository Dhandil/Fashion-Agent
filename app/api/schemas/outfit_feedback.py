"""Outfit 用户反馈 API 数据结构。"""

from typing import Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.domain.entities.outfit_feedback import (
    OutfitFeedbackSentiment,
)


class OutfitFeedbackUpsertRequest(BaseModel):
    """新增或覆盖一套已保存穿搭的当前反馈。"""

    # 用户可以只写具体原因，因此态度不是必填项
    sentiment: OutfitFeedbackSentiment | None = None

    # 文字反馈用于记录用户喜欢或不喜欢的具体部分
    comment: str | None = Field(
        default=None,
        max_length=1000,
    )

    @field_validator("comment")
    @classmethod
    def normalize_comment(
        cls,
        comment: str | None,
    ) -> str | None:
        """去除文字反馈首尾空格，并把纯空白内容视为空。"""

        if comment is None:
            return None

        normalized_comment = comment.strip()

        return normalized_comment or None

    @model_validator(mode="after")
    def validate_feedback_content(self) -> Self:
        """确保态度和文字说明至少提供一项。"""

        if (
            self.sentiment is None
            and self.comment is None
        ):
            raise ValueError(
                "反馈态度和文字说明至少需要提供一项",
            )

        return self


class OutfitFeedbackResponse(BaseModel):
    """当前用户对一套 Outfit 的反馈响应。"""

    outfit_id: str
    sentiment: OutfitFeedbackSentiment | None = None
    comment: str | None = None

    # 允许直接从不可变领域实体读取响应字段
    model_config = ConfigDict(
        from_attributes=True,
    )


class OutfitFeedbackListItem(BaseModel):
    """最近反馈列表中的一项，并附带原穿搭摘要。"""

    outfit_id: str
    outfit_name: str
    scenario: str
    sentiment: OutfitFeedbackSentiment | None = None
    comment: str | None = None


class OutfitFeedbackListResponse(BaseModel):
    """当前用户最近 Outfit 反馈列表。"""

    items: tuple[OutfitFeedbackListItem, ...] = ()
    count: int = Field(
        ge=0,
    )
    limit: int = Field(
        ge=1,
    )
