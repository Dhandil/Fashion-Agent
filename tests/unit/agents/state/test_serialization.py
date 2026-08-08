"""Agent State 持久化模型兼容转换测试。"""

from app.agents.state.serialization import coerce_model, model_to_json
from app.domain.entities.outfit import OutfitItem, OutfitRecommendation


def test_model_to_json_accepts_restored_dictionary() -> None:
    """验证 Redis 恢复的字典可以重新渲染为 JSON。"""

    recommendation = OutfitRecommendation(
        name="清爽通勤",
        scenario="通勤",
        items=(
            OutfitItem(
                role="上装",
                name="浅蓝色衬衫",
                source="wardrobe",
                source_reference_id="shirt-001",
            ),
        ),
        recommendation_reason="适合通勤。",
    )

    restored = recommendation.model_dump(mode="json")
    rendered = model_to_json(restored)

    assert '"name":"清爽通勤"' in rendered
    assert '"source_reference_id":"shirt-001"' in rendered


def test_coerce_model_discards_incomplete_persisted_state() -> None:
    """验证不完整的旧派生状态不会阻塞新一轮对话。"""

    assert coerce_model(
        {"legacy_field": "outdated"},
        OutfitRecommendation,
    ) is None
