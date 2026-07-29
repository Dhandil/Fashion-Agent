"""购物 Agent 系统提示词测试。"""

from app.agents.prompts.shopping import (
    SHOPPING_ASSISTANT_SYSTEM_PROMPT,
)


def test_shopping_prompt_defines_information_sources() -> None:
    """验证系统提示词明确区分商品工具和知识库职责。"""

    # 具体商品查询必须使用商品搜索工具
    assert "必须调用 search_products 工具" in (
        SHOPPING_ASSISTANT_SYSTEM_PROMPT
    )

    # 工具无结果时不得虚构商品
    assert "工具返回空列表时" in (
        SHOPPING_ASSISTANT_SYSTEM_PROMPT
    )

    # 知识库不能代替工具提供具体商品数据
    assert "不能代替商品工具提供具体商品数据" in (
        SHOPPING_ASSISTANT_SYSTEM_PROMPT
    )

    # 当前系统不允许执行真实交易
    assert "不执行购买、支付、下单或修改库存" in (
        SHOPPING_ASSISTANT_SYSTEM_PROMPT
    )