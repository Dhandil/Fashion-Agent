"""用户对已保存 Outfit 的反馈领域实体。"""

from enum import StrEnum
from typing import Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class OutfitFeedbackSentiment(StrEnum):
    """用户对一套 Outfit 的明确态度。"""

    LIKE = "like"
    DISLIKE = "dislike"


class OutfitFeedback(BaseModel):
    """用户对一套已保存穿搭的当前反馈。"""

    # 用户身份由服务端注入，不能由 LLM 或请求正文指定
    user_id: str = Field(
        min_length=1,
        max_length=100,
    )

    # 反馈必须关联一套属于该用户的已保存 Outfit
    outfit_id: str = Field(
        min_length=1,
        max_length=100,
    )

    # 用户可以只写文字反馈，因此态度允许为空
    sentiment: OutfitFeedbackSentiment | None = None

    # 用户主动提供的具体原因或调整方向
    comment: str | None = Field(
        default=None,
        max_length=1000,
    )

    model_config = ConfigDict(
        frozen=True,
    )

    @field_validator("comment")
    @classmethod
    def normalize_comment(
        cls,
        comment: str | None,
    ) -> str | None:
        """去除文字反馈首尾空格并把空白内容归一为空。"""

        if comment is None:
            return None

        normalized_comment = comment.strip()

        return normalized_comment or None

    @model_validator(mode="after")
    def validate_feedback_content(self) -> Self:
        """验证态度和文字反馈至少提供一项。"""

        if (
            self.sentiment is None
            and self.comment is None
        ):
            raise ValueError(
                "反馈态度和文字说明至少需要提供一项",
            )

        return self
