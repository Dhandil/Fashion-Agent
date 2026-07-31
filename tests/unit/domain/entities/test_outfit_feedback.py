"""Outfit 用户反馈领域实体测试。"""

import pytest
from pydantic import ValidationError

from app.domain.entities.outfit_feedback import (
    OutfitFeedback,
    OutfitFeedbackSentiment,
)


def test_feedback_accepts_sentiment_and_comment() -> None:
    """验证反馈可以同时包含态度和具体说明。"""

    feedback = OutfitFeedback(
        user_id="user-001",
        outfit_id="outfit-001",
        sentiment="like",
        comment="  配色很适合通勤  ",
    )

    assert (
        feedback.sentiment
        is OutfitFeedbackSentiment.LIKE
    )
    assert feedback.comment == "配色很适合通勤"


def test_feedback_accepts_comment_without_sentiment() -> None:
    """验证用户可以只提供具体调整意见。"""

    feedback = OutfitFeedback(
        user_id="user-001",
        outfit_id="outfit-001",
        comment="希望下装更休闲一些",
    )

    assert feedback.sentiment is None
    assert feedback.comment == "希望下装更休闲一些"


def test_feedback_requires_sentiment_or_comment() -> None:
    """验证完全空白的反馈不能进入长期数据。"""

    with pytest.raises(
        ValidationError,
        match="至少需要提供一项",
    ):
        OutfitFeedback(
            user_id="user-001",
            outfit_id="outfit-001",
            comment="   ",
        )
