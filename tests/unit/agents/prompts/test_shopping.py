"""Fashion Agent 系统提示词测试。"""

from app.agents.prompts.shopping import (
    SHOPPING_ASSISTANT_SYSTEM_PROMPT,
)


def test_prompt_defines_fashion_agent_positioning() -> None:
    """验证系统提示词以穿搭决策作为核心能力。"""

    # Agent 的身份应该是个人穿搭与衣橱助手
    assert "个人穿搭与衣橱助手" in (
        SHOPPING_ASSISTANT_SYSTEM_PROMPT
    )

    # 穿搭方案应该优先于商品推荐
    assert "穿搭方案优先，商品推荐其次" in (
        SHOPPING_ASSISTANT_SYSTEM_PROMPT
    )

    # Agent 应优先帮助用户使用已有衣物
    assert "优先帮助用户使用已有衣物" in (
        SHOPPING_ASSISTANT_SYSTEM_PROMPT
    )

    # 没有衣橱数据时不得假装用户拥有某件衣物
    assert "不得声称某件衣物是用户已经拥有的" in (
        SHOPPING_ASSISTANT_SYSTEM_PROMPT
    )


def test_prompt_defines_tool_and_data_boundaries() -> None:
    """验证提示词明确区分衣橱、知识库和商品工具。"""

    # 普通穿搭建议不应该自动搜索商品
    assert "普通穿搭建议不得默认调用商品搜索工具" in (
        SHOPPING_ASSISTANT_SYSTEM_PROMPT
    )

    # 具体商品搜索必须通过真实工具完成
    assert "才调用 search_products 工具" in (
        SHOPPING_ASSISTANT_SYSTEM_PROMPT
    )

    # 工具没有结果时不能虚构商品
    assert "工具返回空列表时" in (
        SHOPPING_ASSISTANT_SYSTEM_PROMPT
    )

    # 知识库不能代替用户衣橱或真实商品数据
    assert "不能代替用户衣橱数据或商品工具提供具体事实" in (
        SHOPPING_ASSISTANT_SYSTEM_PROMPT
    )

    # 没有天气工具时不能虚构实时天气
    assert "不得虚构当前天气" in (
        SHOPPING_ASSISTANT_SYSTEM_PROMPT
    )

    # Agent 当前不允许执行真实交易
    assert "不执行购买、支付、下单、物流、售后或修改库存" in (
        SHOPPING_ASSISTANT_SYSTEM_PROMPT
    )