"""Agent 的结构化 Outfit 生成结果。"""

from pydantic import BaseModel, Field

from app.domain.entities.outfit import (
    OutfitRecommendation,
)


class OutfitGenerationResult(BaseModel):
    """结构化模型对本轮是否生成 Outfit 的判断。"""

    outfit: OutfitRecommendation | None = Field(
        default=None,
        description=("用户明确需要完整穿搭且信息充分时返回推荐，否则返回 null"),
    )
