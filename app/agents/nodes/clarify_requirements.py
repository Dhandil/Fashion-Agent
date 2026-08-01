"""根据结构化缺失字段生成最小追问。"""

from langchain_core.messages import AIMessage

from app.agents.schemas.requirements import RequirementField
from app.agents.state.shopping import ShoppingAgentState

_FIELD_LABELS = {
    RequirementField.SCENARIO: "使用场景",
    RequirementField.TARGET_DATE: "穿着日期",
    RequirementField.LOCATION: "地点",
    RequirementField.FORMALITY: "正式程度",
    RequirementField.STYLE: "希望的风格",
    RequirementField.ITEM_CATEGORY: "需要的衣物品类",
    RequirementField.BUDGET: "预算范围",
    RequirementField.WEATHER: "天气情况",
}


def clarify_requirements(
    state: ShoppingAgentState,
) -> dict[str, list[AIMessage]]:
    """不调用业务工具，只询问分析结果中的必要字段。"""

    analysis = state.get("requirement_analysis")
    if analysis is None or not analysis.missing_fields:
        message = "请再说明一下你希望解决的穿搭问题。"
    else:
        missing_labels = "、".join(_FIELD_LABELS[field] for field in analysis.missing_fields)
        message = f"为了给出更准确且可执行的建议，请补充：{missing_labels}。"

    return {
        "messages": [
            AIMessage(content=message),
        ],
    }
