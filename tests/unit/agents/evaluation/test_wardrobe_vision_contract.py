"""衣物视觉识别结构契约测试。"""

from app.agents.evaluation.wardrobe_vision import validate_vision_contract


def create_item(draft_id: str = "draft-1") -> dict[str, object]:
    """创建合法草稿响应。"""

    return {
        "draft_id": draft_id,
        "name": "白色T恤",
        "category": "T恤",
        "confidence": 0.9,
        "missing_fields": [],
        "uncertain_fields": [],
        "requires_confirmation": True,
    }


def test_contract_accepts_single_and_multi_item_payloads() -> None:
    """验证单件和多件响应都满足结构契约。"""

    single = validate_vision_contract(create_item())
    multi = validate_vision_contract(
        {"items": [create_item("draft-1"), create_item("draft-2")]},
    )

    assert single.passed is True
    assert multi.passed is True
    assert multi.item_count == 2


def test_contract_rejects_duplicate_ids_and_missing_confirmation() -> None:
    """验证重复草稿 ID 和未要求确认的结果会被拒绝。"""

    item = create_item()
    item["requires_confirmation"] = False
    result = validate_vision_contract({"items": [item, item]})

    assert result.passed is False
    assert any("draft_id 重复" in error for error in result.errors)
    assert any("必须要求用户确认" in error for error in result.errors)
