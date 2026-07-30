"""用户衣橱搜索工具。"""

import json

from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, Field

from app.domain.entities.wardrobe_item import (
    WardrobeItemStatus,
)
from app.domain.repositories.wardrobe import (
    WardrobeRepository,
)


class WardrobeSearchInput(BaseModel):
    """衣橱搜索工具的模型输入参数。"""

    # 可选衣物品类，例如衬衫、长裤或鞋履
    category: str | None = Field(
        default=None,
        max_length=100,
        description="需要查询的衣物品类",
    )

    # 限制返回数量，避免向模型发送过多衣橱数据
    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="最多返回的可用衣物数量",
    )


def create_wardrobe_search_tool(
    repository: WardrobeRepository,
    user_id: str,
) -> BaseTool:
    """创建绑定指定用户和衣橱仓库的搜索工具。"""

    @tool(
        args_schema=WardrobeSearchInput,
    )
    async def search_wardrobe(
        category: str | None = None,
        limit: int = 20,
    ) -> str:
        """查询当前用户衣橱中可以参与穿搭的衣物。"""

        # user_id 由应用层注入，模型不能查询其他用户
        wardrobe_items = await repository.search(
            user_id=user_id,
            category=category,
            status=WardrobeItemStatus.AVAILABLE,
            limit=limit,
        )

        # 将领域实体转换为模型可以读取的 JSON 数据
        wardrobe_data = [
            wardrobe_item.model_dump(mode="json")
            for wardrobe_item in wardrobe_items
        ]

        return json.dumps(
            wardrobe_data,
            ensure_ascii=False,
        )

    return search_wardrobe